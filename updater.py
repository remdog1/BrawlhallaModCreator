"""Optional GitHub release discovery and verified portable downloads. No UI imports."""
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import threading
import time
from urllib.parse import urlparse

import requests
from packaging.version import Version, InvalidVersion

from app_version import VERSION, PRERELEASE, UPDATE_REPOSITORY, UPDATE_ASSET

RELEASES_URL = f'https://github.com/{UPDATE_REPOSITORY}/releases'
MAX_DOWNLOAD = 2 * 1024**3


def state_dir():
    return Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'BrawlhallaModCreator' / 'Updates'


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name, dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(data, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def read_json(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return default


@dataclass(frozen=True)
class Release:
    version: str
    notes: str
    url: str
    size: int
    digest: str
    prerelease: bool


def select_release(releases, current=VERSION, allow_beta=PRERELEASE):
    choices = []
    for release in releases:
        if release.get('draft') or (release.get('prerelease') and not allow_beta):
            continue
        try:
            version = Version(release.get('tag_name', '').removeprefix('v'))
        except InvalidVersion:
            continue
        if version <= Version(current) or (version.is_prerelease and not allow_beta):
            continue
        assets = [asset for asset in release.get('assets', []) if asset.get('name') == UPDATE_ASSET]
        if len(assets) != 1:
            continue
        asset = assets[0]
        url = asset.get('browser_download_url', '')
        if not url.startswith(RELEASES_URL + '/download/') or urlparse(url).fragment:
            continue
        size = asset.get('size', 0)
        if not isinstance(size, int) or not 0 < size <= MAX_DOWNLOAD:
            continue
        digest = asset.get('digest') or ''
        if not re.fullmatch(r'sha256:[0-9a-fA-F]{64}', digest):
            digest = ''
        choices.append((version, Release(str(version), release.get('body') or 'No release notes provided.',
                                        url, size, digest.removeprefix('sha256:').lower(),
                                        bool(release.get('prerelease')))))
    return max(choices, key=lambda item: item[0])[1] if choices else None


class UpdateClient:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers['User-Agent'] = f'BrawlhallaModCreator/{VERSION}'
        self.etag = None
        self.cached = None

    def check(self):
        headers = {'If-None-Match': self.etag} if self.etag and self.cached is not None else {}
        with self.session.get(f'https://api.github.com/repos/{UPDATE_REPOSITORY}/releases?per_page=100',
                              headers=headers, timeout=(5, 10)) as response:
            if response.status_code == 304:
                releases = self.cached
            else:
                response.raise_for_status()
                releases = response.json()
                if not isinstance(releases, list):
                    raise ValueError('Unexpected GitHub release response')
                self.etag, self.cached = response.headers.get('ETag'), releases
        return select_release(releases), bool(releases)

    def download(self, release, folder, cancel, progress):
        if not release.digest:
            raise ValueError('This release has no SHA-256 digest. Use the release page or republish the asset.')
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        if shutil.disk_usage(folder).free < release.size * 3 + 64 * 1024**2:
            raise OSError('Not enough free disk space for the update and backup')
        target = folder / 'payload.exe'
        partial = folder / 'payload.part'
        url = release.url
        started = time.monotonic()
        try:
            for _ in range(6):
                parsed = urlparse(url)
                if (parsed.scheme != 'https' or parsed.username or parsed.password or
                        parsed.hostname not in ('github.com', 'release-assets.githubusercontent.com',
                                                'objects.githubusercontent.com')):
                    raise ValueError('Untrusted update download location')
                response = self.session.get(url, stream=True, allow_redirects=False, timeout=(5, 20))
                if response.is_redirect:
                    url = response.headers.get('Location', '')
                    response.close()
                    continue
                break
            else:
                raise ValueError('Too many download redirects')
            digest, count = hashlib.sha256(), 0
            with response, partial.open('wb') as output:
                response.raise_for_status()
                for chunk in response.iter_content(1024 * 1024):
                    if cancel.is_set():
                        raise InterruptedError('Download cancelled')
                    if time.monotonic() - started > 1800:
                        raise TimeoutError('Download exceeded 30 minutes')
                    count += len(chunk)
                    if count > release.size:
                        raise ValueError('Downloaded file is larger than the published asset')
                    digest.update(chunk)
                    output.write(chunk)
                    progress(count, release.size)
            if count != release.size or digest.hexdigest() != release.digest:
                raise ValueError('Update size or SHA-256 verification failed; the current app is unchanged')
            with partial.open('rb') as stream:
                if stream.read(2) != b'MZ':
                    raise ValueError('The release asset is not a Windows executable')
            os.replace(partial, target)
            return target
        finally:
            partial.unlink(missing_ok=True)


def prepare_update(release, payload):
    if not getattr(sys, 'frozen', False):
        raise RuntimeError('Source checkouts cannot replace themselves with a release executable')
    import psutil
    target = Path(sys.executable).resolve()
    # A writable sibling staging directory also tests permission before the app exits.
    staging = Path(tempfile.mkdtemp(prefix='.creator-update-', dir=target.parent))
    try:
        shutil.copy2(payload, staging / 'payload.exe')
        shutil.copy2(target, staging / 'helper.exe')
        process = psutil.Process()
        job = dict(target=str(target), version=release.version, notes=release.notes,
                   digest=release.digest, parent_pid=process.pid, parent_created=process.create_time())
        write_json(staging / 'job.json', job)
        return staging / 'helper.exe', staging / 'job.json'
    except Exception:
        # Only remove the newly allocated directory, never the user's app folder.
        if staging.resolve().parent == target.parent and staging.name.startswith('.creator-update-'):
            shutil.rmtree(staging)
        raise
