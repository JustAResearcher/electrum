# Electrum-MEWC — Lightweight Meowcoin client

```
Licence: MIT Licence
Upstream: spesmilo/electrum (Bitcoin) v4.7.2
Language: Python (>= 3.10)
Repository: https://github.com/JustAResearcher/electrum (branch: meowcoin)
Releases:   https://github.com/JustAResearcher/electrum/releases
```

A Meowcoin (Apex v30.2+) port of the [Electrum](https://github.com/spesmilo/electrum) Bitcoin wallet, adapted to talk to [`electrs-mewc`](https://github.com/Meowcoin-Foundation/electrs-mewc) backends and parse Meowcoin's variable-size block headers (80-byte pre-KAWPOW / AuxPoW + 120-byte KAWPOW/MEOWPOW).

## Quick install

**Windows**: download `electrum-vX.Y.Z-mewc.N-setup.exe` from the [releases page](https://github.com/JustAResearcher/electrum/releases).

**Linux / from source**:
```
sudo apt-get install libsecp256k1-dev
pip install Electrum-X.Y.Z+mewc.N.tar.gz   # from the releases page
```

URI scheme is `meowcoin:`.

## What's adapted from upstream Electrum

- **Chainparams** ([electrum/constants.py](electrum/constants.py)): P2PKH=50 (`M…`), P2SH=122 (`m…`), WIF=112, bech32 `mewc`/`tmewc`, BIP44=1669, default ports 50001/50002.
- **Variable-size headers** ([electrum/blockchain.py](electrum/blockchain.py)): 80-byte (pre-KAWPOW + AuxPoW) and 120-byte (KAWPOW/MEOWPOW) parsing, with disk-padding to 120 so seek-by-height arithmetic stays simple.
- **Trust model**: KAWPOW/MEOWPOW block hashes can't be computed client-side without a ProgPoW implementation, so `verify_header` is a no-op and `can_connect` skips `prev_hash` / PoW checks. Chain integrity is delegated to the `electrs-mewc` backend; tx signing, addresses, merkle proofs, and confirmations work normally.
- **Branding** ([electrum/gui/icons/](electrum/gui/icons/)): Meowcoin Foundation icon set (gold atom + pixel cat). All `Bitcoin`/`BTC` user-visible strings rebranded to `Meowcoin`/`MEWC`. URI scheme is `meowcoin:`.
- **Lightning Network is disabled**: Meowcoin has no LN deployment, so `LIGHTNING_AVAILABLE = False` in `MeowcoinMainnet` short-circuits `can_have_lightning()` and hides all enable-LN UI.
- **OS integration**: `electrum.desktop`, NSIS Windows installer, macOS pyinstaller, Android intent filter and buildozer spec all register the `meowcoin:` scheme.

## Known limitations (v1)

- **No client-side PoW verification** (see "Trust model" above).
- **No asset support yet**: Meowcoin's RIP5/HIP2 asset transactions (issue, transfer, restricted, qualifier, message-channel) are not parsed by this wallet. Inputs/outputs containing assets get parsed as plain MEWC.
- **macOS .dmg not yet shipped**: upstream's `make_osx.sh` builds libzbar from source, which fails on `macos-latest` arm64. Tracked.
- **AppImage not yet shipped**: upstream type2-runtime Dockerfile pins outdated Alpine package versions. Tracked.
- **Hardware wallet (Trezor / Ledger / Coldcard)** entries don't natively know Meowcoin's BIP44 coin type 1669; they treat addresses as Bitcoin. Real support would need device-firmware patches.
- **Exchange-rate price feeds** in `electrum/exchange_rate.py` query Bitcoin price APIs unchanged — fiat values shown for MEWC will be wrong until MEWC-specific endpoints are wired in.

## Default servers

```json
{
  "meowelectrum2.testtopper.biz": {"s": "50002", "t": "50001", "version": "1.4.2", "pruning": "-"},
  "electrum.mewccrypto.com":      {"s": "50002", "t": "50001", "version": "1.4.2", "pruning": "-"}
}
```

Both run ElectrumX-Meowcoin 2.x and serve KAWPOW/MEOWPOW (120-byte) headers.

## Building / contributing

The CI workflow at [.github/workflows/release.yml](.github/workflows/release.yml) builds Windows installer + Linux sdist + Android APK on tag push (`v*`). Pre-existing upstream build scripts in [contrib/](contrib/) (`build-linux/sdist`, `build-wine`, `osx`, `android`) are reused; the PEP 440 version string lives in [electrum/version.py](electrum/version.py).

To verify the chainparams + header round-trip without setting up the full GUI deps:

```bash
python C:/Source/_mewc_research/smoke_test.py   # see commit history; fakes ecc to skip libsecp DLL
```

## Upstream

This is a fork of [spesmilo/electrum](https://github.com/spesmilo/electrum) v4.7.2. Bug reports and ideas that aren't Meowcoin-specific should be reported there.

---

## Getting started

_(If you've come here looking to simply run Electrum,
[you may download it here](https://electrum.org/#download).)_

Electrum itself is pure Python, and so are most of the required dependencies,
but not everything. The following sections describe how to run from source, but here
is a TL;DR:

```
$ sudo apt-get install libsecp256k1-dev
$ ELECTRUM_ECC_DONT_COMPILE=1 python3 -m pip install --user ".[gui,crypto]"
```

### Not pure-python dependencies

#### Qt GUI

If you want to use the Qt interface, install the Qt dependencies:
```
$ sudo apt-get install python3-pyqt6
```

#### libsecp256k1

For elliptic curve operations,
[libsecp256k1](https://github.com/bitcoin-core/secp256k1)
is a required dependency.

If you "pip install" Electrum, by default libsecp will get compiled locally,
as part of the `electrum-ecc` dependency. This can be opted-out of,
by setting the `ELECTRUM_ECC_DONT_COMPILE=1` environment variable.
For the compilation to work, besides a C compiler, you need at least:
```
$ sudo apt-get install automake libtool
```
If you opt out of the compilation, you need to provide libsecp in another way, e.g.:
```
$ sudo apt-get install libsecp256k1-dev
```

#### cryptography

Due to the need for fast symmetric ciphers,
[cryptography](https://github.com/pyca/cryptography) is required.
Install from your package manager (or from pip):
```
$ sudo apt-get install python3-cryptography
```

#### hardware-wallet support

If you would like hardware wallet support,
[see this](https://github.com/spesmilo/electrum-docs/blob/master/hardware-linux.rst).


### Running from tar.gz

If you downloaded the official package (tar.gz), you can run
Electrum from its root directory without installing it on your
system; all the pure python dependencies are included in the 'packages'
directory. To run Electrum from its root directory, just do:
```
$ ./run_electrum
```

You can also install Electrum on your system, by running this command:
```
$ sudo apt-get install python3-setuptools python3-pip
$ python3 -m pip install --user .
```

This will download and install the Python dependencies used by
Electrum instead of using the 'packages' directory.
It will also place an executable named `electrum` in `~/.local/bin`,
so make sure that is on your `PATH` variable.


### Development version (git clone)

_(For OS-specific instructions, see [here for Windows](contrib/build-wine/README_windows.md),
and [for macOS](contrib/osx/README_macos.md))_

Check out the code from GitHub:
```
$ git clone https://github.com/spesmilo/electrum.git
$ cd electrum
$ git submodule update --init
```

Run install (this should install dependencies):
```
$ python3 -m pip install --user -e .
```

Create translations (optional):
```
$ sudo apt-get install gettext
$ ./contrib/locale/build_locale.sh electrum/locale/locale electrum/locale/locale
```

Finally, to start Electrum:
```
$ ./run_electrum
```

### Run tests

Run unit tests with `pytest`:
```
$ pytest tests -v
```
(can be parallelized with `-n auto` option, using [`pytest-xdist`](https://github.com/pytest-dev/pytest-xdist) plugin)

To run a single file, specify it directly like this:
```
$ pytest tests/test_bitcoin.py -v
```

## Creating Binaries

- [Linux (tarball)](contrib/build-linux/sdist/README.md)
- [Linux (AppImage)](contrib/build-linux/appimage/README.md)
- [macOS](contrib/osx/README.md)
- [Windows](contrib/build-wine/README.md)
- [Android](contrib/android/Readme.md)


## Contributing

Any help testing the software, reporting or fixing bugs, reviewing pull requests
and recent changes, writing tests, or helping with outstanding issues is very welcome.
Implementing new features, or improving/refactoring the codebase, is of course
also welcome, but to avoid wasted effort, especially for larger changes,
we encourage discussing these on the issue tracker or IRC first.

Besides [GitHub](https://github.com/spesmilo/electrum),
most communication about Electrum development happens on IRC, in the
`#electrum` channel on Libera Chat. The easiest way to participate on IRC is
with the web client, [web.libera.chat](https://web.libera.chat/#electrum).

Please improve translations on [Crowdin](https://crowdin.com/project/electrum).
