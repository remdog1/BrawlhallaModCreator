import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch

from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QLabel, QCheckBox
from ui.ui_handler import updater as ui_updater
from updater import Release, write_json, read_json
from app_version import VERSION


class UpdateUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.state_patch = patch.object(ui_updater, 'state_dir', lambda: self.root)
        self.state_patch.start()
        self.window = QMainWindow()
        self.window.header = types.SimpleNamespace(updateButton=QPushButton(self.window))
        self.window.progressDialog = types.SimpleNamespace(isShown=lambda: False)
        self.updater = ui_updater.CreatorUpdater(self.window)

    def tearDown(self):
        if self.updater.dialog:
            self.updater.dialog.reject()
        self.window.close()
        self.window.deleteLater()
        self.app.processEvents()
        self.state_patch.stop()
        self.temp.cleanup()

    def test_offline_automatic_is_silent_manual_explains_failure(self):
        self.updater._checked(None, 'Connection failed; offline use remains available.', False)
        self.assertIsNone(self.updater.dialog)
        self.updater._checked(None, 'Connection failed; offline use remains available.', True)
        self.assertIn('offline', self.updater.dialog.findChild(QLabel).text())

    def test_source_mode_displays_versions_without_install_button(self):
        release = Release('0.2.8', 'New feature\nFixed bug', '', 6, '0' * 64, False)
        self.updater._checked(release, '', True)
        label = self.updater.dialog.findChild(QLabel).text()
        self.assertIn(VERSION, label)
        self.assertIn('0.2.8', label)
        texts = [button.text() for button in self.updater.dialog.findChildren(QPushButton)]
        self.assertNotIn('Update Now', texts)
        self.assertIn('Open Releases', texts)

    def test_automatic_setting_persists(self):
        self.updater._dialog('Updates', 'Settings')
        self.updater.dialog.findChild(QCheckBox).setChecked(False)
        self.updater.dialog.reject()
        self.assertFalse(read_json(self.root / 'settings.json')['automatic'])

    def test_notes_display_once_only_for_installed_version(self):
        target = self.root / 'Creator.exe'
        write_json(self.root / 'installed.json', dict(version=VERSION, target=str(target), notes='Test notes'))
        with patch.object(ui_updater.sys, 'frozen', True, create=True), \
             patch.object(ui_updater.sys, 'executable', str(target)):
            self.updater._show_completed()
            self.assertEqual(self.updater.dialog.windowTitle(), 'Update Complete')
            self.updater.dialog.reject()
            self.updater._show_completed()
            self.assertIsNone(self.updater.dialog)


if __name__ == '__main__':
    unittest.main()
