"""Explicit build diagnostic; writes only to its supplied report folder."""
import json
import multiprocessing
import os
from pathlib import Path
import traceback
import tempfile


def check_worker(queue, folder):
    try:
        import jpype
        import win32api
        from PySide6.QtWidgets import QApplication
        from core.core import ffdec
        from core.core.swf.swf import Swf

        os.environ['QT_QPA_PLATFORM'] = 'offscreen'
        app = QApplication([])
        path = str(Path(tempfile.mkdtemp(prefix='swf-', dir=folder)) / 'runtime-check.bmod')
        payload = b'Creator bundled runtime roundtrip'
        swf = Swf(path)
        swf.importBinaryData(payload, 1)
        swf.save()
        swf.close()
        swf.open()
        assert swf.exportBinaryData(elId=1) == payload
        swf.close()
        queue.put({'ok': True, 'java': list(jpype.getJVMVersion()),
                   'jvm': ffdec.jvmpath, 'jpype': jpype.__version__,
                   'qt': app.platformName(), 'swf_roundtrip': True})
    except BaseException:
        queue.put({'ok': False, 'traceback': traceback.format_exc()})


def run_check(report_path):
    report = Path(report_path).resolve()
    report.parent.mkdir(parents=True, exist_ok=True)
    os.environ['APPDATA'] = str(report.parent / 'appdata')
    os.environ.pop('BMOD_PYINSTALLER_ANALYSIS', None)
    context = multiprocessing.get_context('spawn')
    queue = context.Queue()
    worker = context.Process(target=check_worker, args=(queue, str(report.parent)))
    worker.start()
    try:
        result = queue.get(timeout=90)
    except Exception:
        result = {'ok': False, 'error': 'Runtime check worker did not report within 90 seconds'}
    finally:
        worker.join(timeout=10)
        if worker.is_alive():
            worker.terminate()
            worker.join(timeout=10)
    result['worker_exitcode'] = worker.exitcode
    report.write_text(json.dumps(result, indent=2), encoding='utf-8')
    return 0 if result.get('ok') and worker.exitcode == 0 else 1
