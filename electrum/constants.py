# -*- coding: utf-8 -*-
#
# Electrum - lightweight Meowcoin client (forked from Bitcoin Electrum)
# Copyright (C) 2018 The Electrum developers
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import os
import json
from typing import Sequence, Tuple, Mapping, Type, List, Optional

from .lntransport import LNPeerAddr
from .util import inv_dict, all_subclasses, classproperty
from . import bitcoin


def read_json(filename, default=None):
    path = os.path.join(os.path.dirname(__file__), filename)
    try:
        with open(path, 'r') as f:
            r = json.loads(f.read())
    except Exception:
        if default is None:
            # Sometimes it's better to hard-fail: the file might be missing
            # due to a packaging issue, which might otherwise go unnoticed.
            raise
        r = default
    return r


def create_fallback_node_list(fallback_nodes_dict: dict[str, dict]) -> List[LNPeerAddr]:
    """Take a json dict of fallback nodes like: k:node_id, v:{k:'host', k:'port'} and return LNPeerAddr list"""
    fallback_nodes = []
    for node_id, address in fallback_nodes_dict.items():
        fallback_nodes.append(
            LNPeerAddr(host=address['host'], port=int(address['port']), pubkey=bytes.fromhex(node_id)))
    return fallback_nodes


GIT_REPO_URL = "https://github.com/JustAResearcher/electrum"
GIT_REPO_ISSUES_URL = "https://github.com/JustAResearcher/electrum/issues"
RELEASE_NOTES_URL = "https://raw.githubusercontent.com/JustAResearcher/electrum/refs/heads/meowcoin/RELEASE-NOTES"
BIP39_WALLET_FORMATS = read_json('bip39_wallet_formats.json')


# Meowcoin block-header activation timestamps (from Meowcoin Core kernel/chainparams.cpp).
# Used by blockchain.py to detect 80-byte vs 120-byte header format.
KAWPOW_ACTIVATION_TIME_MAINNET = 1662493424
KAWPOW_ACTIVATION_TIME_TESTNET = 1661833868

# AuxPoW version flag (bit 8): blocks with this bit set use the 80-byte
# pure header on the wire (electrs-mewc strips the AuxPoW blob server-side).
VERSION_AUXPOW_BIT = 0x100


class AbstractNet:

    NET_NAME: str
    TESTNET: bool
    WIF_PREFIX: int
    ADDRTYPE_P2PKH: int
    ADDRTYPE_P2SH: int
    SEGWIT_HRP: str
    BOLT11_HRP: str
    GENESIS: str
    BLOCK_HEIGHT_FIRST_LIGHTNING_CHANNELS: int = 0
    BIP44_COIN_TYPE: int
    LN_REALM_BYTE: int
    DEFAULT_PORTS: Mapping[str, str]
    LN_DNS_SEEDS: Sequence[str]
    XPRV_HEADERS: Mapping[str, int]
    XPRV_HEADERS_INV: Mapping[int, str]
    XPUB_HEADERS: Mapping[str, int]
    XPUB_HEADERS_INV: Mapping[int, str]
    KAWPOW_ACTIVATION_TIME: int = 0  # 0 means "always pre-KAWPOW" (regtest etc.)
    # Lightning Network support gate. False on Meowcoin (no LN deployment);
    # gates can_have_lightning() so the enable UI is hidden everywhere.
    LIGHTNING_AVAILABLE: bool = False

    @classmethod
    def max_checkpoint(cls) -> int:
        return max(0, len(cls.CHECKPOINTS) * 2016 - 1)

    @classmethod
    def rev_genesis_bytes(cls) -> bytes:
        return bytes.fromhex(cls.GENESIS)[::-1]

    @classmethod
    def set_as_network(cls) -> None:
        global net
        net = cls

    _cached_default_servers = None
    @classproperty
    def DEFAULT_SERVERS(cls) -> Mapping[str, Mapping[str, str]]:
        if cls._cached_default_servers is None:
            default_file = {} if cls.TESTNET else None  # for mainnet we hard-fail if the file is missing.
            cls._cached_default_servers = read_json(os.path.join('chains', cls.NET_NAME, 'servers.json'), default_file)
        return cls._cached_default_servers

    _cached_fallback_lnnodes = None
    @classproperty
    def FALLBACK_LN_NODES(cls) -> Sequence[LNPeerAddr]:
        if cls._cached_fallback_lnnodes is None:
            default_file = {} if cls.TESTNET else None  # for mainnet we hard-fail if the file is missing.
            d = read_json(os.path.join('chains', cls.NET_NAME, 'fallback_lnnodes.json'), default_file)
            cls._cached_fallback_lnnodes = create_fallback_node_list(d)
        return cls._cached_fallback_lnnodes

    _cached_checkpoints = None
    @classproperty
    def CHECKPOINTS(cls) -> Sequence[Tuple[str, int]]:
        if cls._cached_checkpoints is None:
            default_file = [] if cls.TESTNET else None  # for mainnet we hard-fail if the file is missing.
            cls._cached_checkpoints = read_json(os.path.join('chains', cls.NET_NAME, 'checkpoints.json'), default_file)
        return cls._cached_checkpoints

    @classmethod
    def datadir_subdir(cls) -> Optional[str]:
        """The name of the folder in the filesystem.
        None means top-level, used by mainnet.
        """
        return cls.NET_NAME

    @classmethod
    def cli_flag(cls) -> str:
        """as used in e.g. `$ run_electrum --testnet4`"""
        return cls.NET_NAME

    @classmethod
    def config_key(cls) -> str:
        """as used for SimpleConfig.get()"""
        return cls.NET_NAME


class MeowcoinMainnet(AbstractNet):

    NET_NAME = "mainnet"
    TESTNET = False
    # WIF private-key prefix (Meowcoin uses 112 = 0x70).
    WIF_PREFIX = 112
    # P2PKH addresses start with 'M' (version byte 50).
    ADDRTYPE_P2PKH = 50
    # P2SH addresses start with 'm' (version byte 122).
    ADDRTYPE_P2SH = 122
    SEGWIT_HRP = "mewc"
    BOLT11_HRP = SEGWIT_HRP  # Lightning is not deployed on Meowcoin; kept to satisfy code paths.
    # Meowcoin genesis (X16R hash, asserted by Meowcoin Core for testnet; mainnet hash matches).
    GENESIS = "000000edd819220359469c54f2614b5602ebc775ea67a64602f354bdaa320f70"
    # Default Electrum protocol ports for electrs-mewc (TCP / TLS).
    DEFAULT_PORTS = {'t': '50001', 's': '50002'}
    # Lightning is not deployed on Meowcoin.
    BLOCK_HEIGHT_FIRST_LIGHTNING_CHANNELS = 0
    KAWPOW_ACTIVATION_TIME = KAWPOW_ACTIVATION_TIME_MAINNET

    # Standard BIP32 extended-key version bytes (same as Bitcoin/Meowcoin Core).
    XPRV_HEADERS = {
        'standard':    0x0488ade4,  # xprv
        'p2wpkh-p2sh': 0x049d7878,  # yprv
        'p2wsh-p2sh':  0x0295b005,  # Yprv
        'p2wpkh':      0x04b2430c,  # zprv
        'p2wsh':       0x02aa7a99,  # Zprv
    }
    XPRV_HEADERS_INV = inv_dict(XPRV_HEADERS)
    XPUB_HEADERS = {
        'standard':    0x0488b21e,  # xpub
        'p2wpkh-p2sh': 0x049d7cb2,  # ypub
        'p2wsh-p2sh':  0x0295b43f,  # Ypub
        'p2wpkh':      0x04b24746,  # zpub
        'p2wsh':       0x02aa7ed3,  # Zpub
    }
    XPUB_HEADERS_INV = inv_dict(XPUB_HEADERS)
    # Meowcoin BIP44 coin type (registered: 1669).
    BIP44_COIN_TYPE = 1669
    LN_REALM_BYTE = 0
    LN_DNS_SEEDS = []  # Lightning not deployed on Meowcoin.

    @classmethod
    def datadir_subdir(cls):
        return None


class MeowcoinTestnet(AbstractNet):

    NET_NAME = "testnet"
    TESTNET = True
    WIF_PREFIX = 114
    ADDRTYPE_P2PKH = 109  # 'm'
    ADDRTYPE_P2SH = 124
    SEGWIT_HRP = "tmewc"
    BOLT11_HRP = SEGWIT_HRP
    GENESIS = "000000eaab417d6dfe9bd75119972e1d07ecfe8ff655bef7c2acb3d9a0eeed81"
    DEFAULT_PORTS = {'t': '51001', 's': '51002'}
    KAWPOW_ACTIVATION_TIME = KAWPOW_ACTIVATION_TIME_TESTNET

    XPRV_HEADERS = {
        'standard':    0x04358394,  # tprv
        'p2wpkh-p2sh': 0x044a4e28,  # uprv
        'p2wsh-p2sh':  0x024285b5,  # Uprv
        'p2wpkh':      0x045f18bc,  # vprv
        'p2wsh':       0x02575048,  # Vprv
    }
    XPRV_HEADERS_INV = inv_dict(XPRV_HEADERS)
    XPUB_HEADERS = {
        'standard':    0x043587cf,  # tpub
        'p2wpkh-p2sh': 0x044a5262,  # upub
        'p2wsh-p2sh':  0x024289ef,  # Upub
        'p2wpkh':      0x045f1cf6,  # vpub
        'p2wsh':       0x02575483,  # Vpub
    }
    XPUB_HEADERS_INV = inv_dict(XPUB_HEADERS)
    BIP44_COIN_TYPE = 1
    LN_REALM_BYTE = 1
    LN_DNS_SEEDS = []


class MeowcoinRegtest(MeowcoinTestnet):

    NET_NAME = "regtest"
    SEGWIT_HRP = "mewcrt"
    BOLT11_HRP = SEGWIT_HRP
    # Regtest genesis is recomputed at first run; placeholder that matches Meowcoin Core regtest seed.
    GENESIS = "0f9188f13cb7b2c71f2a335e3a4fc328bf5beb436012afca590b1a11466e2206"
    LN_DNS_SEEDS = []
    KAWPOW_ACTIVATION_TIME = 0  # regtest stays on legacy 80-byte format


# Aliases kept so any external imports of the old Bitcoin* names still resolve.
BitcoinMainnet = MeowcoinMainnet
BitcoinTestnet = MeowcoinTestnet
BitcoinRegtest = MeowcoinRegtest


NETS_LIST = tuple(all_subclasses(AbstractNet))  # type: Sequence[Type[AbstractNet]]
NETS_LIST = tuple(sorted(NETS_LIST, key=lambda x: x.NET_NAME))

assert len(NETS_LIST) == len(set([chain.NET_NAME for chain in NETS_LIST])), "NET_NAME must be unique for each concrete AbstractNet"
assert len(NETS_LIST) == len(set([chain.datadir_subdir() for chain in NETS_LIST])), "datadir must be unique for each concrete AbstractNet"
assert len(NETS_LIST) == len(set([chain.cli_flag() for chain in NETS_LIST])), "cli_flag must be unique for each concrete AbstractNet"
assert len(NETS_LIST) == len(set([chain.config_key() for chain in NETS_LIST])), "config_key must be unique for each concrete AbstractNet"

# don't import net directly, import the module instead (so that net is singleton)
net = MeowcoinMainnet  # type: Type[AbstractNet]
