# Electrum-MEWC port notes

Living design + status doc for the Meowcoin port of Electrum. Written against
upstream commit at the time of fork (`v4.7.2`) and Meowcoin Core branch
`Meow_v30.2.0`.

---

## 1. What's intentionally not implemented yet

These are deliberate gaps tracked here so future sessions don't re-discover them:

### 1.1 Client-side block-hash verification (security-relevant)

**Status**: `verify_header()` is a no-op and `can_connect()` skips
`prev_hash` checks. Chain integrity is fully delegated to the
electrs-mewc / ElectrumX-Meowcoin backend.

**Why**: Meowcoin block hashes (post-KAWPOW activation, 2022-09-06) are
KAWPOW or MEOWPOW ProgPoW hashes, not SHA256d. Computing these client-side
in pure Python takes ~seconds per header — roughly ten thousand times
slower than verifying SHA256d. For a wallet syncing 1.9M+ headers that's
infeasible. Bitcoin Electrum's `hash_header()` uses SHA256d on the wire
bytes; we keep that as a stable internal **fingerprint** but it does not
match the network's view of "the hash of block N."

**Impact**: a malicious server can feed us a fabricated chain that doesn't
correspond to real Meowcoin work. We'd notice if its merkle proofs failed
(merkle is still SHA256d on txids — that part works), and we'd notice if
two trusted servers disagreed. But absent that, we're trusting one server.
Acceptable for everyday wallet use; not acceptable for high-value cold
storage without an independent verifier.

**Two paths to fix**:

#### Path A — server-trust-anchored hash overlay (recommended)

Have the server return `(height, real_block_hash)` pairs alongside the
header bytes. Client stores them in a side-table keyed by height, and the
chain-linking checks compare overlay-hash vs `header.prev_block_hash`
instead of recomputing `hash_header()`.

Required:

- New optional electrum-protocol RPC, e.g. `blockchain.block.header_with_hash`
  returning `{"hex": "<header bytes>", "hash": "<real KAWPOW hash>"}`.
  electrs-mewc would gain this method (Meowcoin Core RPC already has the
  hash via `getblockhash`/`getblockheader`).
- Client-side change: `electrum/blockchain.py` grows a `HashOverlay` class
  backed by a JSON file at `~/.electrum-mewc/header_hashes.json`.
- `verify_chunk` consults the overlay; mismatch → reject the chunk and
  swap to a different server.
- A "mismatch between trusted servers" alarm in the GUI.

This still requires *trusting* the server's claimed hash, but at least
makes that trust explicit and detectable rather than silent.

Estimated work: ~3-5 days. Hardest part is shipping electrs-mewc with the
new RPC.

#### Path B — pure-Python KAWPOW/MEOWPOW (rejected)

Implementing ProgPoW client-side. Realistically a 1-2 month effort; even
then performance would be ~1 hash/sec, which is too slow to verify a
historical sync. Useful only as a sanity-check on a few canary blocks.
Not worth pursuing.

---

### 1.2 Meowcoin asset support (RIP5 / HIP2)

**Status**: not parsed. Inputs/outputs containing assets are decoded as
plain MEWC by the upstream Bitcoin transaction parser. Asset-bearing
transactions will display incorrect amounts and the user can accidentally
"send" an asset by burning it as fees.

**Scope of what's needed** (rough order of dependency):

1. **Tx parsing** — Meowcoin Core wraps asset metadata inside a non-standard
   `OP_RVN_ASSET` opcode (0xc0) embedded in the scriptPubKey. The parser
   in `electrum/transaction.py` needs to recognize the opcode and split
   the script into "regular P2PKH/P2SH" + "asset metadata" portions.
   The metadata layout is documented in
   [Meowcoin/src/assets/assettypes.h](https://github.com/Meowcoin-Foundation/Meowcoin/blob/Meow_v30.2.0/src/assets/assettypes.h).
   Eight asset types: standard, sub, unique, message-channel, qualifier,
   sub-qualifier, restricted, null-qualifier-tag. Each has its own
   serialization schema.

2. **Wallet storage** — extend `electrum/wallet.py` to track per-asset
   balances next to the MEWC balance. New on-disk format, migration code
   for existing wallet files.

3. **Address synchronizer** — `electrum/address_synchronizer.py` needs an
   asset-aware UTXO model so the coin chooser doesn't accidentally spend
   asset outputs as MEWC inputs.

4. **Coin chooser** — `electrum/coinchooser.py` needs to filter UTXOs by
   asset id so an asset transfer only consumes UTXOs of that asset.

5. **GUI** — new "Assets" tab listing held assets, balances, and recent
   transfers; "Send" tab dropdown to pick which asset to send; "Issue
   asset" wizard with the burn-fee + ownership-token semantics.

6. **RPC** — new commands: `listassets`, `getassetbalance`, `sendasset`,
   `issueasset`, `reissueasset`, `transferasset`, `addtagtoaddress`, etc.

7. **Server protocol** — electrs-mewc would ideally return an
   `asset_summary` field per UTXO. If it doesn't, the client can derive it
   from the raw scriptPubKey on its own.

**Reference implementation**: the
[`electrum-meowcoin`](https://github.com/Meowcoin-Foundation/electrum-meowcoin)
fork (which is built on the older Electrum 4.0.x branch and ElectrumX 1.11
protocol) has working asset support. Worth porting forward rather than
re-implementing — most of the asset-parsing code is straight Python with
no protocol dependencies.

**Estimated work**: 4-6 weeks for full feature parity with the prior fork.

---

### 1.3 Hardware wallet support

**Status (as of v4.7.2-mewc.6)**: hardware wallet plugins are now **disabled
at the loader level** by a `HW_WALLETS_SUPPORTED = False` gate on
`MeowcoinMainnet`, checked in `electrum/plugin.py:find_directory_plugins()`
before the plugin gets registered. Plugins still ship in the source tree
(`electrum/plugins/{trezor,ledger,coldcard,bitbox02,jade,keepkey,safe_t}/`)
so re-enabling is a one-line config change once vendor firmware lands.

The reason: Meowcoin's registered BIP44 coin type is **1669**
([SLIP-44](https://github.com/satoshilabs/slips/blob/master/slip-0044.md))
and no shipping vendor firmware recognises it. Loading these plugins
without firmware support produces silent address-derivation refusals at
sign time.

**Why this is a problem**: a hardware wallet device asked to derive an
address at `m/44'/1669'/0'/0/0` will refuse — its firmware doesn't recognize
coin type 1669 as "Meowcoin". It'll either:

- Treat it as an unknown / generic coin, requiring the user to verify each
  address manually on-device with no human-readable label, **or**
- Refuse the derivation entirely.

**Realistic paths**:

1. **Device firmware patches** (cleanest, requires Meowcoin Foundation
   coordination): submit PRs to Trezor / Ledger / Coldcard / etc. to
   register Meowcoin in their coin database. Each vendor has its own
   review process; expect months per vendor.

2. **Use coin type 0 with explicit warnings** (current default-of-defaults):
   the wallet derives at the Bitcoin path. Same hardware-key reuse as a
   Bitcoin wallet — addresses on-device display as Bitcoin addresses but
   our wallet renders them with the MEWC version byte. **Dangerous** if
   the user ever actually opens the same device in a Bitcoin wallet —
   sending those coins would look like a Bitcoin transaction to the
   device but is actually a Meowcoin one.

3. **Software-only signing** (most robust, no hardware): a watching-only
   wallet here + sign on a separate offline machine using the desktop
   Electrum-MEWC. Loses hardware-wallet UX but no firmware risk.

**Recommendation**: ship v1 with hardware wallet plugins removed or
hard-disabled, and document option 3 in the README. Once Meowcoin
Foundation lands the SLIP-44 entry in the major vendors' firmware,
re-enable.

---

## 2. Already-shipped pieces of the port

For continuity if/when this doc is read in a future session:

- Chainparams: `electrum/constants.py` (`MeowcoinMainnet`, `MeowcoinTestnet`)
- Variable-size headers (80 / 120 byte): `electrum/blockchain.py`
- Wire-format detection: `electrum/blockchain.py:_wire_header_size()`
- Lightning hard-disabled: `electrum/wallet.py:can_have_lightning()`
  via `constants.LIGHTNING_AVAILABLE`
- Hardware wallets hard-disabled at plugin loader: `electrum/plugin.py`
  via `constants.HW_WALLETS_SUPPORTED`
- BIP21 URI scheme `meowcoin:`: `electrum/bip21.py`
- MEWC price feed via CoinGecko `meowcoin` id: `electrum/exchange_rate.py`
- Server list: `electrum/chains/mainnet/servers.json` — three
  electrs-mewc deployments (`electrs-esplora 0.4.1`), all confirmed
  serving 120-byte KAWPOW headers
- Auto-update checker: `electrum/gui/qt/update_checker.py` points at
  this fork's GitHub Releases API; signature verification skipped
  (trust shifts to the HTTPS connection to api.github.com)
- OS integration files (`.desktop`, NSIS, pyinstaller, Android intent)
  all register `meowcoin:` URI scheme
- CI: `.github/workflows/release.yml` builds Linux sdist + AppImage,
  Windows installer + portable, macOS .dmg, Android .apk on tag push;
  uploads to the GitHub Release with SHA256SUMS

### 2.1 Testnet status

`electrum/chains/testnet/servers.json` is intentionally empty (`{}`).
No public Meowcoin testnet electrs / ElectrumX deployment is reachable
on the obvious hostnames (`testnet-electrs.mewccrypto.com`,
`electrs-testnet.mewccrypto.com`, `testnet.mewccrypto.com`,
`testnet-electrs.meowcoin.org`, etc.). Once one is stood up, drop the
hostname and ports into `chains/testnet/servers.json` and the
`--testnet` flag works.

## 3. Verified end-to-end against live network (2026-05-06)

Against `electrum.mewccrypto.com:50001`:

```
$ blockchain.headers.subscribe → height=1902286, header bytes=120
$ blockchain.estimatefee(2)    → 0.01119014 MEWC
$ blockchain.relayfee          → 0.01 MEWC
$ getbalance(MCBurnXXX...)     → 2,502,839.92 MEWC confirmed
```

The chainparams P2PKH version byte (50), bech32 HRP (`mewc`), Electrum
scripthash convention (sha256(scriptpubkey)[::-1].hex()), and 120-byte
KAWPOW header parsing all check out against the live mainnet.
