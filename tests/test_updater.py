import hashlib
import json
import os
from pathlib import Path
import tempfile
import threading
import types
import unittest
from unittest.mock import patch

import updater
import update_helper
from app_version import UPDATE_ASSET


def release(tag='v0.2.8', **changes):
    value = dict(tag_name=tag, prerelease=False, body='Release notes', assets=[dict(
        name=UPDATE_ASSET, size=6, digest='sha256:' + hashlib.sha256(b'MZtest').hexdigest(),
        browser_download_url=updater.RELEASES_URL + '/download/' + tag + '/' + UPDATE_ASSET)])
    value.update(changes)
    return value


class Response:
    is_redirect = False
    headers = {}
    status_code = 200

    def __init__(self, payload=b'MZtest'):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def raise_for_status(self):
        pass

    def iter_content(self, size):
        yield self.payload


class UpdaterTests(unittest.TestCase):
    def test_versions_no_downgrade_and_not_lexical(self):
        self.assertIsNone(updater.select_release([release('v0.2.6')], '0.2.7'))
        self.assertEqual(updater.select_release([release('v0.2.9'), release('v0.2.10')], '0.2.7').version, '0.2.10')

    def test_stable_beta_and_drafts(self):
        self.assertIsNone(updater.select_release([release('v0.3.0b1', prerelease=True)], '0.2.7', False))
        self.assertIsNone(updater.select_release([release(draft=True)], '0.2.7'))
        self.assertEqual(updater.select_release([release('v0.3.0')], '0.3.0b1').version, '0.3.0')

    def test_asset_name_and_origin_required(self):
        raw = release()
        raw['assets'][0]['name'] = 'ModLoader.exe'
        self.assertIsNone(updater.select_release([raw]))
        raw = release()
        raw['assets'][0]['browser_download_url'] = 'https://example.org/app.exe'
        self.assertIsNone(updater.select_release([raw]))

    def test_successful_download_and_progress(self):
        client = updater.UpdateClient()
        client.session = types.SimpleNamespace(get=lambda *a, **k: Response())
        with tempfile.TemporaryDirectory() as folder:
            progress = []
            path = client.download(updater.select_release([release()]), folder, threading.Event(),
                                   lambda *args: progress.append(args))
            self.assertEqual(path.read_bytes(), b'MZtest')
            self.assertEqual(progress, [(6, 6)])

    def test_corrupt_or_cancelled_download_is_not_staged(self):
        for data, cancelled in [(b'MZbad!', False), (b'MZ', False), (b'MZtest', True)]:
            client = updater.UpdateClient()
            client.session = types.SimpleNamespace(get=lambda *a, **k: Response(data))
            cancel = threading.Event()
            if cancelled:
                cancel.set()
            with tempfile.TemporaryDirectory() as folder:
                with self.assertRaises((ValueError, InterruptedError)):
                    client.download(updater.select_release([release()]), folder, cancel, lambda *args: None)
                self.assertFalse((Path(folder) / 'payload.exe').exists())
                self.assertFalse((Path(folder) / 'payload.part').exists())

    def test_no_digest_disables_install(self):
        raw = release()
        raw['assets'][0]['digest'] = None
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError, 'SHA-256'):
                updater.UpdateClient().download(updater.select_release([raw]), folder, threading.Event(), print)

    def helper_fixture(self, root):
        target = root / 'Creator.exe'
        target.write_bytes(b'old version')
        folder = root / '.creator-update-test'
        folder.mkdir()
        (folder / 'payload.exe').write_bytes(b'MZnew version')
        updater.write_json(folder / 'job.json', dict(target=str(target), version='0.2.8', notes='New notes',
            digest=hashlib.sha256(b'MZnew version').hexdigest(), parent_pid=999999, parent_created=0))
        return target, folder / 'job.json'

    def test_helper_replaces_only_executable_and_saves_notes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target, job = self.helper_fixture(root)
            mods = root / 'Mods Sources'
            mods.mkdir()
            (mods / 'keep.txt').write_text('keep')
            launched = []
            with patch.object(update_helper, 'state_dir', lambda: root / 'state'), \
                 patch.object(update_helper.psutil, 'Process', side_effect=update_helper.psutil.NoSuchProcess(999999)):
                self.assertEqual(update_helper.apply_update(job, launched.append), 0)
            self.assertEqual(target.read_bytes(), b'MZnew version')
            self.assertEqual((root / 'Creator.exe.previous-test').read_bytes(), b'old version')
            self.assertEqual((mods / 'keep.txt').read_text(), 'keep')
            self.assertEqual(launched, [target])
            self.assertEqual(updater.read_json(root / 'state/installed.json')['notes'], 'New notes')

    def test_failed_launch_restores_backup(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target, job = self.helper_fixture(root)
            with patch.object(update_helper, 'state_dir', lambda: root / 'state'), \
                 patch.object(update_helper.psutil, 'Process', side_effect=update_helper.psutil.NoSuchProcess(999999)):
                def fail(path):
                    raise OSError('launch denied')
                self.assertEqual(update_helper.apply_update(job, fail), 1)
            self.assertEqual(target.read_bytes(), b'old version')
            self.assertFalse((root / 'state/installed.json').exists())

    def test_running_parent_is_not_killed_or_replaced(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target, job = self.helper_fixture(root)
            process = types.SimpleNamespace(create_time=lambda: 0, is_running=lambda: True)
            with patch.object(update_helper, 'state_dir', lambda: root / 'state'), \
                 patch.object(update_helper.psutil, 'Process', return_value=process):
                self.assertEqual(update_helper.apply_update(job, lambda p: None, wait_seconds=0), 1)
            self.assertEqual(target.read_bytes(), b'old version')


if __name__ == '__main__':
    unittest.main()
