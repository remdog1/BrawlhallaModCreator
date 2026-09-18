import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import webbrowser

from PySide6.QtCore import QObject, Signal, QTimer, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (QCheckBox, QDialog, QDialogButtonBox, QLabel,
                              QMessageBox, QProgressDialog, QTextBrowser, QVBoxLayout)

from app_version import VERSION
from updater import UpdateClient, RELEASES_URL, prepare_update, state_dir, read_json, write_json

UPDATE_STYLE = '''
QDialog, QProgressDialog { background: #292b30; color: #eeeeef; }
QLabel, QCheckBox { color: #eeeeef; }
QTextBrowser { background: #202226; color: #eeeeef; border: 1px solid #505259; padding: 8px; }
QPushButton { background: #42454c; color: #ffffff; border: 1px solid #62656d;
              border-radius: 4px; padding: 7px 14px; min-height: 20px; }
QPushButton:hover { background: #52565f; }
'''


class CreatorUpdater(QObject):
    checked = Signal(object, str, bool)
    progressed = Signal(object, object)
    staged = Signal(object, str)

    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.client = UpdateClient()
        self.busy = False
        self.dialog = None
        self.progress = None
        self.cancel = threading.Event()
        self.checked.connect(self._checked)
        self.progressed.connect(self._progressed)
        self.staged.connect(self._staged)

    def startup(self):
        self._show_completed()
        settings = read_json(state_dir() / 'settings.json', {})
        if settings.get('automatic', True):
            self.check(False)

    def _set_busy(self, busy):
        self.busy = busy
        self.window.header.updateButton.setEnabled(not busy)

    def check(self, manual=True):
        if self.busy or self.dialog is not None:
            return
        self._set_busy(True)

        def worker():
            try:
                release, published = self.client.check()
                message = ('No newer compatible release is available.' if published else
                           'No releases have been published yet.')
                self.checked.emit(release, message, manual)
            except Exception as error:
                self.checked.emit(None, f'Could not check for updates. You can keep using the creator offline.\n\n{error}', manual)
        threading.Thread(target=worker, daemon=True).start()

    def _checked(self, release, message, manual):
        self._set_busy(False)
        if release is None:
            if manual:
                self._dialog('Check for Updates', f'Installed version: {VERSION}\n\n{message}')
            return
        if self.window.progressDialog.isShown():
            QTimer.singleShot(2000, lambda: self._checked(release, message, manual))
            return
        text = f'Installed: {VERSION}\nAvailable: {release.version}\n\nSave your changes before updating. The creator will close and restart.'
        can_install = getattr(sys, 'frozen', False) and bool(release.digest)
        if not getattr(sys, 'frozen', False):
            text += '\n\nThis is a source checkout. Updates will not overwrite your working code; use the release page for the EXE.'
        elif not release.digest:
            text += '\n\nThis asset has no verification digest. Automatic installation is disabled.'
        self._dialog('Update Available', text, release.notes,
                     ('Update Now', lambda: self.download(release)) if can_install else
                     ('Open Releases', lambda: webbrowser.open(RELEASES_URL)))

    def _dialog(self, title, text, notes=None, action=None):
        if self.dialog is not None:
            return
        dialog = QDialog(self.window)
        self.dialog = dialog
        dialog.setWindowTitle(title)
        dialog.setFont(QFont('Roboto', 10))
        dialog.setStyleSheet(UPDATE_STYLE)
        dialog.setWindowModality(Qt.WindowModal)
        dialog.resize(540, 430 if notes else 240)
        layout = QVBoxLayout(dialog)
        label = QLabel(text)
        label.setTextFormat(Qt.PlainText)
        label.setWordWrap(True)
        layout.addWidget(label)
        if notes:
            browser = QTextBrowser()
            # No remote image loads or HTML execution from release notes.
            browser.setPlainText(notes)
            browser.setOpenExternalLinks(False)
            layout.addWidget(browser)
        automatic = QCheckBox('Check for updates when the creator starts')
        automatic.setChecked(read_json(state_dir() / 'settings.json', {}).get('automatic', True))
        layout.addWidget(automatic)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        if action:
            buttons.button(QDialogButtonBox.Close).setText('Later')
            button = buttons.addButton(action[0], QDialogButtonBox.AcceptRole)
            button.clicked.connect(lambda: (dialog.accept(), action[1]()))
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        def finished(_):
            self.dialog = None
            try:
                write_json(state_dir() / 'settings.json', {'automatic': automatic.isChecked()})
            except OSError:
                pass
            dialog.deleteLater()
        dialog.finished.connect(finished)
        dialog.open()

    def download(self, release):
        if self.busy or self.window.progressDialog.isShown():
            QMessageBox.information(self.window, 'Update', 'Finish the current mod operation before updating.')
            return
        self._set_busy(True)
        self.cancel.clear()
        self.progress = QProgressDialog('Downloading update...', 'Cancel', 0, 100, self.window)
        self.progress.setWindowTitle('Creator Update')
        self.progress.setFont(QFont('Roboto', 10))
        self.progress.setStyleSheet(UPDATE_STYLE)
        self.progress.setWindowModality(Qt.WindowModal)
        self.progress.setAutoClose(False)
        self.progress.setAutoReset(False)
        self.progress.canceled.connect(self.cancel.set)
        self.progress.show()

        def worker():
            try:
                with tempfile.TemporaryDirectory(prefix='creator-download-') as folder:
                    payload = self.client.download(release, folder, self.cancel, self.progressed.emit)
                    if self.cancel.is_set():
                        raise InterruptedError('Download cancelled')
                    paths = prepare_update(release, payload)
                self.staged.emit(paths, '')
            except Exception as error:
                self.staged.emit(None, str(error))
        threading.Thread(target=worker, daemon=True).start()

    def _progressed(self, done, total):
        if self.progress is not None:
            self.progress.setValue(min(99, done * 100 // total))

    def _staged(self, paths, error):
        cancelled = self.cancel.is_set()
        if self.progress is not None:
            self.progress.close()
            self.progress.deleteLater()
            self.progress = None
        self._set_busy(False)
        if paths is None:
            if not cancelled:
                self._dialog('Update Not Installed', error + '\n\nYour current version is unchanged.')
            return
        if cancelled or self.window.progressDialog.isShown():
            self._dialog('Update Not Installed', 'The update was cancelled or a mod operation is active. Your current version is unchanged.')
            return
        helper, job = paths
        try:
            env = os.environ.copy()
            env['PYINSTALLER_RESET_ENVIRONMENT'] = '1'
            env['PYINSTALLER_SUPPRESS_SPLASH_SCREEN'] = '1'
            subprocess.Popen([str(helper), '--apply-update', str(job)], cwd=helper.parent,
                             env=env, close_fds=True, creationflags=subprocess.CREATE_NO_WINDOW)
        except OSError as error:
            self._dialog('Update Not Installed', str(error))
            return
        from main import TerminateApp
        TerminateApp()

    def _show_completed(self):
        failure = read_json(state_dir() / 'failed.json')
        if failure:
            self._dialog('Update Failed', 'The update did not complete. The previous version was preserved.', failure.get('error', 'Unknown error'))
            try:
                (state_dir() / 'failed.json').unlink(missing_ok=True)
            except OSError:
                pass
            return
        installed = read_json(state_dir() / 'installed.json')
        if (installed and getattr(sys, 'frozen', False) and installed.get('version') == VERSION and
                Path(installed.get('target', '')).resolve() == Path(sys.executable).resolve()):
            self._dialog('Update Complete', f'You are now running version {VERSION}.', installed.get('notes'))
            try:
                (state_dir() / 'installed.json').unlink(missing_ok=True)
            except OSError:
                pass
