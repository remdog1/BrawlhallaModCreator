"""Runs from a separate copy of the frozen app, before UI or Java imports."""
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

import psutil
from updater import read_json, write_json, state_dir


def restart(target):
    env = os.environ.copy()
    env['PYINSTALLER_RESET_ENVIRONMENT'] = '1'
    subprocess.Popen([str(target)], cwd=target.parent, env=env, close_fds=True)


def apply_update(job_path, launch=restart, wait_seconds=120):
    job_path = Path(job_path).resolve()
    folder = job_path.parent
    backup = None
    replaced = False
    try:
        job = read_json(job_path)
        if not isinstance(job, dict):
            raise ValueError('Invalid update job')
        target = Path(job['target']).resolve()
        payload = folder / 'payload.exe'
        if (folder.parent != target.parent or not folder.name.startswith('.creator-update-') or
                target.suffix.lower() != '.exe' or target.name in ('payload.exe', 'helper.exe')):
            raise ValueError('Update target must be beside its staging directory')
        with payload.open('rb') as stream:
            if hashlib.file_digest(stream, 'sha256').hexdigest() != job['digest']:
                raise ValueError('Staged update failed SHA-256 verification')
        deadline = time.monotonic() + wait_seconds
        while True:
            try:
                parent = psutil.Process(job['parent_pid'])
                alive = parent.create_time() == job['parent_created'] and parent.is_running()
            except psutil.NoSuchProcess:
                alive = False
            if not alive:
                break
            if time.monotonic() >= deadline:
                raise TimeoutError('Creator is still running; update was not installed')
            time.sleep(0.25)
        backup = target.with_name(target.name + '.previous-' + folder.name.removeprefix('.creator-update-'))
        # The one-file launcher may release its EXE just after the Python process exits.
        while True:
            try:
                os.replace(target, backup)
                break
            except PermissionError:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(0.25)
        try:
            os.replace(payload, target)
            replaced = True
            write_json(state_dir() / 'installed.json', dict(version=job['version'], notes=job['notes'],
                                                          target=str(target), backup=str(backup)))
            launch(target)
        except Exception:
            if backup.exists():
                os.replace(backup, target)
            replaced = False
            (state_dir() / 'installed.json').unlink(missing_ok=True)
            raise
        write_json(folder / 'result.json', {'ok': True, 'version': job['version']})
        return 0
    except Exception:
        error = traceback.format_exc()
        write_json(folder / 'result.json', {'ok': False, 'error': error})
        write_json(state_dir() / 'failed.json', {'error': error})
        # The old executable remains available. Do not loop through relaunch failures.
        if backup is not None and not replaced and target.exists():
            try:
                launch(target)
            except Exception:
                pass
        return 1


if __name__ == '__main__':
    raise SystemExit(apply_update(sys.argv[1]))
