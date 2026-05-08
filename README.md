# Electrum-MEWC — Lightweight Meowcoin client

```
Licence:    MIT
Upstream:   spesmilo/electrum (Bitcoin) v4.7.2
Language:   Python (>= 3.10)
Repository: https://github.com/JustAResearcher/electrum  (branch: meowcoin)
Releases:   https://github.com/JustAResearcher/electrum/releases
Design notes: docs/PORT_NOTES.md
```

A Meowcoin (Apex v30.2+) port of the [Electrum](https://github.com/spesmilo/electrum) Bitcoin wallet, adapted to talk to [`electrs-mewc`](https://github.com/Meowcoin-Foundation/electrs-mewc) backends and parse Meowcoin's variable-size block headers (80-byte pre-KAWPOW / AuxPoW + 120-byte KAWPOW/MEOWPOW). URI scheme is `meowcoin:`.

## Install

Pick one from the [latest release](https://github.com/JustAResearcher/electrum/releases/latest):

| Platform | Asset |
|---|---|
| Windows  | `electrum-vX.Y.Z-mewc.N-setup.exe` (NSIS installer, registers `meowcoin:` URI). Standalone `.exe` and `-portable.exe` are also published. |
| Linux    | `electrum-vX.Y.Z-mewc.N-x86_64.AppImage` — `chmod +x` then run. |
| Source   | `Electrum-X.Y.Z+mewc.N.tar.gz` — `pip install` after `apt-get install libsecp256k1-dev` (or `brew install secp256k1` on macOS). |

macOS `.dmg` and Android `.apk` are not in the current release matrix — see "Known limitations" below.

Verify with the published `SHA256SUMS`:
```
sha256sum -c SHA256SUMS
```

## Default servers

```json
{
  "electrs.mewccrypto.com":  {"s": "50002", "version": "1.4.2", "pruning": "-"},
  "electrs2.mewccrypto.com": {"s": "50002", "t": "50001", "version": "1.4.2", "pruning": "-"},
  "electrs3.meowcoin.org":   {"s": "50002", "version": "1.4.2", "pruning": "-"}
}
```

All three run `electrs-esplora 0.4.1` and serve 120-byte KAWPOW headers. TLS-only hosts omit the `t` port.

## What's adapted from upstream Electrum

- **Chainparams** ([electrum/constants.py](electrum/constants.py)) — P2PKH=50 (`M…`), P2SH=122 (`m…`), WIF=112, bech32 `mewc` / `tmewc`, BIP44=1669, default ports 50001/50002.
- **Variable-size headers** ([electrum/blockchain.py](electrum/blockchain.py)) — 80-byte (pre-KAWPOW + AuxPoW) and 120-byte (KAWPOW/MEOWPOW) parsing. On disk we pad to 120 so seek-by-height arithmetic stays simple.
- **Trust model** — KAWPOW/MEOWPOW block hashes can't be computed client-side without porting ProgPoW into Electrum, so `verify_header` is a no-op and `can_connect` skips `prev_hash` / PoW checks. Chain integrity is delegated to the `electrs-mewc` backend; tx signing, addresses, merkle proofs, and confirmation counts work normally.
- **Lightning hard-disabled** — `LIGHTNING_AVAILABLE = False` on `MeowcoinMainnet` short-circuits `wallet.can_have_lightning()`. LN UI is hidden everywhere.
- **Hardware wallets hard-disabled** — `HW_WALLETS_SUPPORTED = False` makes `electrum/plugin.py` skip plugins whose `registers_keystore[0] == "hardware"`. Re-enabled with a one-line flip once Trezor / Ledger / Coldcard / BitBox / Jade firmware adds Meowcoin to SLIP-44 (coin type 1669).
- **MEWC fiat price** ([electrum/exchange_rate.py](electrum/exchange_rate.py)) — single CoinGecko adapter querying `/api/v3/simple/price?ids=meowcoin` and `/api/v3/coins/meowcoin/market_chart`. Other Bitcoin-only exchanges removed from the GUI dropdown.
- **Branding** ([electrum/gui/icons/](electrum/gui/icons/)) — Meowcoin Foundation icon set (gold atom + pixel cat); user-visible `Bitcoin` / `BTC` strings rebranded to `Meowcoin` / `MEWC`.
- **OS integration** — `electrum.desktop`, NSIS Windows installer, Android intent filter, and buildozer spec all register the `meowcoin:` scheme.
- **Auto-updater** ([electrum/gui/qt/update_checker.py](electrum/gui/qt/update_checker.py)) — points at this fork's GitHub Releases API; signature verification skipped (trust shifts to HTTPS to api.github.com).

## Known limitations

- **No client-side PoW verification.** See "Trust model" above. Acceptable for everyday wallet use; not recommended for high-value cold storage without an independent verifier. Path forward documented in [docs/PORT_NOTES.md](docs/PORT_NOTES.md) §1.1.
- **Asset support not wired in.** Meowcoin's RIP5/HIP2 asset transactions (issue, transfer, restricted, qualifier, message-channel, etc.) aren't parsed yet. Asset-bearing inputs/outputs decode as plain MEWC. Multi-week project; see [docs/PORT_NOTES.md](docs/PORT_NOTES.md) §1.2.
- **macOS `.dmg` not in current release matrix.** Long failure trail (libzbar → frozenlist Cython → hw deps → arch mismatch on macos-latest → runner-pool depletion on macos-13). Path forward needs either a self-hosted arm64 runner or a `make_osx.sh` rewrite using the macos-14 runner's pre-installed arm64 Python; full notes in the disabled job comment in [.github/workflows/release.yml](.github/workflows/release.yml).
- **Android `.apk` ships single-ABI** (`arm64-v8a` only). All-ABI cold builds exceeded GitHub Actions' 6h job cap. With the `actions/cache@v4` step warm, additional ABIs become cheap and can be re-enabled.
- **Hardware wallets disabled** — see above. Plugins still ship in the source tree, just skipped at the loader.
- **Testnet servers list is empty.** No public Meowcoin testnet electrs is reachable on the obvious hostnames; once one is stood up it goes in `electrum/chains/testnet/servers.json`.

## Building

The release workflow at [.github/workflows/release.yml](.github/workflows/release.yml) builds Linux sdist + AppImage + Windows installer + Android APK on tag push (`v*`) using the upstream `contrib/build-*` scripts. The PEP 440 version string lives in [electrum/version.py](electrum/version.py).

To build locally, see the per-platform READMEs:

- [Linux sdist](contrib/build-linux/sdist/README.md)
- [Linux AppImage](contrib/build-linux/appimage/README.md)
- [Windows](contrib/build-wine/README.md)
- [macOS](contrib/osx/README.md)
- [Android](contrib/android/Readme.md)

## Running from source

```bash
sudo apt-get install libsecp256k1-dev python3-pyqt6
git clone https://github.com/JustAResearcher/electrum.git
cd electrum
git submodule update --init
ELECTRUM_ECC_DONT_COMPILE=1 pip install --user -e ".[gui]"
./run_electrum
```

For testing, run `pytest tests/ -v` (parallelized with `-n auto` if `pytest-xdist` is installed).

## Upstream

This is a fork of [spesmilo/electrum](https://github.com/spesmilo/electrum) at v4.7.2. Bug reports and ideas that aren't Meowcoin-specific should go upstream.
