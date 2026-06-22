"""CyberCafe unified graphical installer (PyQt6)."""

from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtCore import QObject, QThread, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QTextEdit,
    QVBoxLayout,
    QWizard,
    QWizardPage,
)

from installer.services.install_engine import launch_application, run_install
from installer.services.payload import (
    DEFAULT_DIRS,
    MAIN_EXE,
    ROLE_CLIENT,
    ROLE_DESCRIPTIONS,
    ROLE_GLOBAL,
    ROLE_LABELS,
    ROLE_LOCAL,
    payload_root,
    role_payload,
)

APP_TITLE = "CyberCafe Setup"
APP_VERSION = "1.0.0"


class InstallWorker(QObject):
    progress = pyqtSignal(str)
    finished = pyqtSignal(bool, str, object)

    def __init__(
        self,
        role: str,
        source: Path,
        dest: Path,
        desktop_shortcut: bool,
        autostart: bool,
        client_watchdog: bool,
    ) -> None:
        super().__init__()
        self.role = role
        self.source = source
        self.dest = dest
        self.desktop_shortcut = desktop_shortcut
        self.autostart = autostart
        self.client_watchdog = client_watchdog

    def run(self) -> None:
        def log(msg: str) -> None:
            self.progress.emit(msg)

        try:
            ok, msg, exe = run_install(
                self.role,
                self.source,
                self.dest,
                desktop_shortcut=self.desktop_shortcut,
                autostart=self.autostart,
                client_watchdog=self.client_watchdog,
                log=log,
            )
            self.finished.emit(ok, msg, exe)
        except Exception as exc:
            self.finished.emit(False, f"Unexpected error: {exc}", None)


class WelcomePage(QWizardPage):
    def __init__(self) -> None:
        super().__init__()
        self.setTitle("Welcome")
        self.setSubTitle("Install CyberCafe for your café network")

        layout = QVBoxLayout(self)
        intro = QLabel(
            "<p style='font-size:13px'>"
            "This wizard installs one component of the CyberCafe suite. "
            "Choose the role that matches this computer:</p>"
            "<ul>"
            "<li><b>Local Server</b> — branch server with admin dashboard</li>"
            "<li><b>Global Server</b> — multi-branch owner hub</li>"
            "<li><b>Client PC</b> — gaming station kiosk software</li>"
            "</ul>"
            "<p>You can run setup (database, admin account, network) immediately after install.</p>"
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        root = payload_root()
        if root is None:
            warn = QLabel(
                "<p style='color:#b45309'><b>Warning:</b> Install payloads were not found. "
                "Build with <code>scripts\\build_installer.bat</code> before distributing this installer.</p>"
            )
            warn.setWordWrap(True)
            layout.addWidget(warn)


class RolePage(QWizardPage):
    def __init__(self) -> None:
        super().__init__()
        self.setTitle("Choose installation type")
        self.setSubTitle("Select what this computer will run")

        layout = QVBoxLayout(self)
        self._radios: dict[str, QRadioButton] = {}

        # Persisted for later pages; completion is driven by isComplete(), not role*.
        self._role_value = QLineEdit(ROLE_LOCAL)
        self._role_value.setVisible(False)
        self.registerField("role", self._role_value)

        for role in (ROLE_LOCAL, ROLE_GLOBAL, ROLE_CLIENT):
            radio = QRadioButton(ROLE_LABELS[role])
            radio.setProperty("role", role)
            radio.toggled.connect(lambda checked, r=role: self._on_role_toggled(r, checked))
            desc = QLabel(ROLE_DESCRIPTIONS[role])
            desc.setWordWrap(True)
            desc.setStyleSheet("color: #555; margin-left: 28px; margin-bottom: 12px;")
            layout.addWidget(radio)
            layout.addWidget(desc)
            self._radios[role] = radio

        self._radios[ROLE_LOCAL].setChecked(True)
        self._role_value.setText(ROLE_LOCAL)

    def _selected_role(self) -> str | None:
        for role, radio in self._radios.items():
            if radio.isChecked():
                return role
        return None

    def isComplete(self) -> bool:
        return self._selected_role() in (ROLE_LOCAL, ROLE_GLOBAL, ROLE_CLIENT)

    def initializePage(self) -> None:
        role = self._selected_role() or ROLE_LOCAL
        self._role_value.setText(role)
        self.completeChanged.emit()

    def _on_role_toggled(self, role: str, checked: bool) -> None:
        if checked:
            self._role_value.setText(role)
            self.completeChanged.emit()

    def validatePage(self) -> bool:
        role = self._selected_role()
        if role in (ROLE_LOCAL, ROLE_GLOBAL, ROLE_CLIENT):
            self._role_value.setText(role)
            return True
        QMessageBox.warning(self, APP_TITLE, "Select an installation type.")
        return False


class OptionsPage(QWizardPage):
    def __init__(self) -> None:
        super().__init__()
        self.setTitle("Install location and options")
        self.setSubTitle("Choose where to install and optional startup behavior")

        layout = QVBoxLayout(self)

        path_row = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setText(DEFAULT_DIRS[ROLE_LOCAL])
        browse = QPushButton("Browse…")
        browse.clicked.connect(self._browse)
        path_row.addWidget(QLabel("Install folder:"))
        path_row.addWidget(self.path_edit, stretch=1)
        path_row.addWidget(browse)
        layout.addLayout(path_row)

        self.chk_desktop = QCheckBox("Create desktop shortcut")
        self.chk_desktop.setChecked(True)
        self.chk_autostart = QCheckBox("Start automatically when Windows logs in")
        self.chk_autostart.setChecked(True)
        self.chk_watchdog = QCheckBox("Install client watchdog service (Client PC only)")
        self.chk_watchdog.setChecked(True)

        layout.addWidget(self.chk_desktop)
        layout.addWidget(self.chk_autostart)
        layout.addWidget(self.chk_watchdog)

        note = QLabel(
            "Installing under Program Files may require running this setup as Administrator."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: #666; margin-top: 8px;")
        layout.addWidget(note)

        self.registerField("install_path*", self.path_edit)
        self.registerField("desktop_shortcut", self.chk_desktop)
        self.registerField("autostart", self.chk_autostart)
        self.registerField("client_watchdog", self.chk_watchdog)

    def initializePage(self) -> None:
        role = self.wizard().field("role")
        if role in DEFAULT_DIRS:
            self.path_edit.setText(DEFAULT_DIRS[role])

    def _browse(self) -> None:
        start = self.path_edit.text() or str(Path.home())
        chosen = QFileDialog.getExistingDirectory(self, "Install folder", start)
        if chosen:
            self.path_edit.setText(chosen)


class InstallPage(QWizardPage):
    def __init__(self) -> None:
        super().__init__()
        self.setTitle("Installing")
        self.setSubTitle("Copying files and configuring shortcuts")
        self.setCommitPage(True)

        layout = QVBoxLayout(self)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(220)
        layout.addWidget(self.progress)
        layout.addWidget(QLabel("Progress:"))
        layout.addWidget(self.log)

        self._installed_exe_field = QLineEdit()
        self._installed_exe_field.setVisible(False)
        self.registerField("installed_exe", self._installed_exe_field)

        self._thread: QThread | None = None
        self._worker: InstallWorker | None = None
        self._started = False
        self._installed_exe: Path | None = None
        self._install_ok = False

    def initializePage(self) -> None:
        if self._started:
            return
        self._started = True
        self.log.clear()
        self._install_ok = False
        self.completeChanged.emit()

        try:
            role = str(self.wizard().field("role") or "").strip()
            install_path = str(self.wizard().field("install_path") or "").strip()
        except Exception as exc:
            self._fail(f"Could not read install settings: {exc}")
            return

        if role not in (ROLE_LOCAL, ROLE_GLOBAL, ROLE_CLIENT):
            self._fail("No installation type selected. Go back and choose Local, Global, or Client.")
            return
        if not install_path:
            self._fail("Install folder is required. Go back and choose a location.")
            return

        source = role_payload(role)
        dest = Path(install_path)

        if source is None:
            self._fail("Payload not found for this role. Rebuild the installer package.")
            return

        self.log.append(f"Role: {ROLE_LABELS.get(role, role)}")
        self.log.append(f"From: {source}")
        self.log.append(f"To:   {dest}")
        self.log.append("")

        self._thread = QThread(self)
        self._worker = InstallWorker(
            role=role,
            source=source,
            dest=dest,
            desktop_shortcut=bool(self.wizard().field("desktop_shortcut")),
            autostart=bool(self.wizard().field("autostart")),
            client_watchdog=bool(self.wizard().field("client_watchdog")),
        )
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.finished.connect(self._thread.quit)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

    def _on_progress(self, msg: str) -> None:
        self.log.append(msg)

    def _on_finished(self, ok: bool, msg: str, exe: object) -> None:
        self.progress.setRange(0, 1)
        self.progress.setValue(1)
        self._install_ok = ok
        self._installed_exe = exe if isinstance(exe, Path) else None
        if ok:
            self.log.append("")
            self.log.append("Ready to finish setup.")
            self._installed_exe_field.setText(str(self._installed_exe) if self._installed_exe else "")
        else:
            self._fail(msg)
        self.completeChanged.emit()

    def _fail(self, msg: str) -> None:
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self._install_ok = False
        self.log.append(f"ERROR: {msg}")
        self.completeChanged.emit()
        QMessageBox.critical(self, APP_TITLE, msg)

    def isComplete(self) -> bool:
        return self._install_ok

    def validatePage(self) -> bool:
        return self._install_ok


class FinishPage(QWizardPage):
    def __init__(self) -> None:
        super().__init__()
        self.setTitle("Installation complete")
        self.setSubTitle("Launch setup to configure database, admin, and network settings")
        self.setFinalPage(True)

        layout = QVBoxLayout(self)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)

        self.chk_launch = QCheckBox("Launch application now (recommended — runs first-time setup)")
        self.chk_launch.setChecked(True)
        layout.addWidget(self.chk_launch)

        self.registerField("launch_app", self.chk_launch)

    def initializePage(self) -> None:
        role = self.wizard().field("role")
        dest = self.wizard().field("install_path")
        exe = MAIN_EXE.get(role, "application")
        self.summary.setText(
            f"<p><b>{ROLE_LABELS.get(role, role)}</b> was installed to:</p>"
            f"<p><code>{dest}</code></p>"
            f"<p>Main program: <code>{exe}</code></p>"
        )


class InstallerWizard(QWizard):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"{APP_TITLE} {APP_VERSION}")
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.setMinimumSize(640, 480)
        self.setOption(QWizard.WizardOption.HaveHelpButton, False)
        self.setOption(QWizard.WizardOption.NoBackButtonOnLastPage, True)
        self.setButtonText(QWizard.WizardButton.CommitButton, "Install")

        self.addPage(WelcomePage())
        self.addPage(RolePage())
        self.addPage(OptionsPage())
        self.addPage(InstallPage())
        self.addPage(FinishPage())

    def done(self, result: int) -> None:
        if result == QWizard.DialogCode.Accepted:
            if self.field("launch_app"):
                path = self.field("installed_exe")
                if path:
                    launch_application(Path(path))
        super().done(result)


def main() -> int:
    def _excepthook(exc_type, exc, tb):
        import traceback
        detail = "".join(traceback.format_exception(exc_type, exc, tb))
        QMessageBox.critical(None, APP_TITLE, f"An unexpected error occurred:\n\n{detail}")
        sys.__excepthook__(exc_type, exc, tb)

    sys.excepthook = _excepthook

    app = QApplication(sys.argv)
    app.setApplicationName(APP_TITLE)
    app.setStyle("Fusion")

    font = QFont()
    font.setPointSize(10)
    app.setFont(font)

    wizard = InstallerWizard()
    wizard.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
