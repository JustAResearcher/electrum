# Copyright (C) 2019 The Electrum developers
# Distributed under the MIT software license, see the accompanying
# file LICENCE or http://www.opensource.org/licenses/mit-license.php

import asyncio
from typing import Optional

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import QVBoxLayout, QLabel, QProgressBar, QHBoxLayout, QPushButton, QDialog

from electrum import version
from electrum.i18n import _
from electrum.util import make_aiohttp_session
from electrum.logging import Logger
from electrum.network import Network
from electrum._vendor.distutils.version import StrictVersion


class UpdateCheck(QDialog, Logger):
    # Electrum-MEWC: point the update checker at this fork's GitHub
    # Releases instead of upstream Electrum's signed-version feed.
    url = "https://api.github.com/repos/JustAResearcher/electrum/releases/latest"
    download_url = "https://github.com/JustAResearcher/electrum/releases/latest"

    # Upstream Electrum's signing keys do not sign our releases — kept here
    # only so other code referencing this constant doesn't break. Signature
    # verification is bypassed in get_update_info() below; trust shifts to
    # the HTTPS connection to api.github.com plus the user's choice to install
    # this fork in the first place.
    VERSION_ANNOUNCEMENT_SIGNING_KEYS = ()

    def __init__(self, *, latest_version=None):
        QDialog.__init__(self)
        self.setWindowTitle('Electrum - ' + _('Update Check'))
        self.content = QVBoxLayout()
        self.content.setContentsMargins(*[10]*4)

        self.heading_label = QLabel()
        self.content.addWidget(self.heading_label)

        self.detail_label = QLabel()
        self.detail_label.setTextInteractionFlags(Qt.TextInteractionFlag.LinksAccessibleByMouse)
        self.detail_label.setOpenExternalLinks(True)
        self.content.addWidget(self.detail_label)

        self.pb = QProgressBar()
        self.pb.setMaximum(0)
        self.pb.setMinimum(0)
        self.content.addWidget(self.pb)

        versions = QHBoxLayout()
        versions.addWidget(QLabel(_("Current version: {}").format(version.ELECTRUM_VERSION)))
        self.latest_version_label = QLabel(_("Latest version: {}").format(" "))
        versions.addWidget(self.latest_version_label)
        self.content.addLayout(versions)

        self.update_view(latest_version)

        self.update_check_thread = UpdateCheckThread()
        self.update_check_thread.checked.connect(self.on_version_retrieved)
        self.update_check_thread.failed.connect(self.on_retrieval_failed)
        self.update_check_thread.start()

        close_button = QPushButton(_("Close"))
        close_button.clicked.connect(self.close)
        self.content.addWidget(close_button)
        self.setLayout(self.content)
        self.show()

    def on_version_retrieved(self, version):
        self.update_view(version)

    def on_retrieval_failed(self):
        self.heading_label.setText('<h2>' + _("Update check failed") + '</h2>')
        self.detail_label.setText(_("Sorry, but we were unable to check for updates. Please try again later."))
        self.pb.hide()

    @staticmethod
    def _strict_version_of(v: str) -> StrictVersion:
        """Parse `version.ELECTRUM_VERSION` style strings (which may carry a
        PEP 440 local-version suffix like '+mewc.9') into a StrictVersion.
        StrictVersion only understands canonical pre-release suffixes; the
        local-version segment is dropped for comparison purposes (we don't
        downgrade a 4.7.2-mewc.10 install over a 4.7.2-mewc.9 latest).
        """
        stripped = v.strip()
        for sep in ('+mewc.', '-mewc.', '+mewc', '-mewc'):
            if sep in stripped:
                stripped = stripped.split(sep, 1)[0]
                break
        return StrictVersion(stripped)

    @staticmethod
    def is_newer(latest_version):
        return latest_version > UpdateCheck._strict_version_of(version.ELECTRUM_VERSION)

    def update_view(self, latest_version=None):
        if latest_version:
            self.pb.hide()
            self.latest_version_label.setText(_("Latest version: {}").format(latest_version))
            if self.is_newer(latest_version):
                self.heading_label.setText('<h2>' + _("There is a new update available") + '</h2>')
                url = "<a href='{u}'>{u}</a>".format(u=UpdateCheck.download_url)
                self.detail_label.setText(_("You can download the new version from {}.").format(url))
            else:
                self.heading_label.setText('<h2>' + _("Already up to date") + '</h2>')
                self.detail_label.setText(_("You are already on the latest version of Electrum."))
        else:
            self.heading_label.setText('<h2>' + _("Checking for updates...") + '</h2>')
            self.detail_label.setText(_("Please wait while Electrum checks for available updates."))


class UpdateCheckThread(QThread, Logger):
    checked = pyqtSignal(object)
    failed = pyqtSignal()

    def __init__(self):
        QThread.__init__(self)
        Logger.__init__(self)
        self.network = Network.get_instance()
        self._fut = None  # type: Optional[asyncio.Future]

    async def get_update_info(self):
        # Electrum-MEWC: GitHub Releases API returns
        #   {"tag_name": "v4.7.2-mewc.4", "name": "Electrum-MEWC v4.7.2-mewc.4", ...}
        # We parse the tag, strip the leading "v" and the "-mewc.N" suffix to
        # produce a StrictVersion-compatible string for comparison against
        # `version.ELECTRUM_VERSION`'s upstream-Electrum portion.
        async with make_aiohttp_session(proxy=self.network.proxy, timeout=120) as session:
            async with session.get(UpdateCheck.url) as result:
                release = await result.json(content_type=None)
                tag = release.get('tag_name', '')
                if not tag:
                    raise Exception(f'GitHub release has no tag_name: {release!r}')
                # Strip "v" prefix and any "-mewc.N" / "+mewc.N" suffix so
                # StrictVersion can parse e.g. "4.7.2".
                stripped = tag.lstrip('v')
                for sep in ('-mewc.', '+mewc.', '-mewc', '+mewc'):
                    if sep in stripped:
                        stripped = stripped.split(sep, 1)[0]
                        break
                self.logger.info(
                    f"latest GitHub release tag={tag!r}, parsed version={stripped!r} "
                    f"(signature verification skipped — trust is the HTTPS connection to api.github.com)"
                )
                return StrictVersion(stripped.strip())

    def run(self):
        if not self.network:
            self.failed.emit()
            return
        self._fut = asyncio.run_coroutine_threadsafe(self.get_update_info(), self.network.asyncio_loop)
        try:
            update_info = self._fut.result()
        except Exception as e:
            self.logger.info(f"got exception: '{repr(e)}'")
            self.failed.emit()
        else:
            self.checked.emit(update_info)

    def stop(self):
        if self._fut:
            self._fut.cancel()
        self.exit()
        self.wait()
