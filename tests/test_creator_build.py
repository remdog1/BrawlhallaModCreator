"""Exercise compiler methods without game discovery or touching real mods."""
import ast
import json
import os
import re
from pathlib import Path
import tempfile
import threading
import traceback
import types
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]


class Notifications:
    def __getattr__(self, name):
        return name


class Package:
    fail_save = False
    instances = []

    def __init__(self, path):
        self.path = Path(path)
        self.data = {}
        self.closed = False
        self.metaData = types.SimpleNamespace(set=lambda data: None)
        self.instances.append(self)

    def importBinaryFile(self, path):
        tag = len(self.data) + 1
        self.data[tag] = Path(path).read_bytes().hex()
        return tag

    def save(self):
        if self.fail_save:
            raise OSError('simulated disk failure')
        self.path.write_text(json.dumps(self.data))

    def close(self):
        self.closed = True


def compiler(events):
    tree = ast.parse((ROOT / 'core/core/worker/mod.py').read_text(encoding='utf-8-sig'))
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'ModSource')
    methods = [node for node in cls.body if isinstance(node, ast.FunctionDef) and
               node.name in ('compile', '_compileInto', 'getElementsCount', '_getTargetFileKey')]
    normalize = lambda value: value.replace('\\', '/').strip('/')
    known = {'Sound.bnk', 'Art/MapA/shared.png', 'Art/MapB/shared.png'}
    env = dict(os=os, tempfile=tempfile, traceback=traceback, Swf=Package,
               NormalizeGameFileKey=normalize,
               ResolveBrawlhallaFileKey=lambda name: name if name in known else None,
               NotificationType=Notifications(), SendNotification=lambda *args: events.append(args),
               MODS_SOURCES_CACHE_FILE='_cache.json', MODS_SOURCES_CACHE_PREVIEW='_previews',
               BRAWLHALLA_SWFS={}, GetElementId=lambda tag: tag)
    exec(compile(ast.Module(body=methods, type_ignores=[]), str(ROOT / 'core/core/worker/mod.py'), 'exec'), env)
    attrs = {node.name: env[node.name] for node in methods}
    attrs.update(_compile_lock=threading.Lock(), regexSpriteFile=re.compile(r'DefineSprite_(\d+)_?(.+|)?'),
                 getPreviewsPaths=lambda self: [],
                 getDict=lambda self: {'files': self.files})
    return type('CompilerHarness', (), attrs)()


class BuildTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'source'
        self.source.mkdir()
        self.events = []
        self.obj = compiler(self.events)
        self.obj.modSourcesPath = str(self.source)
        self.obj.modPath = str(self.root / 'output.bmod')
        self.obj.hash = 'test'
        self.obj.swfs, self.obj.previewsIds, self.obj.files = {}, {}, {'old': 'metadata'}
        Package.fail_save = False
        Package.instances = []

    def test_root_bank_and_distinct_nested_assets_are_included(self):
        for name, data in [('Sound.bnk', b'bank'), ('Art/MapA/shared.png', b'A'),
                           ('Art/MapB/shared.png', b'B'), ('_cache.json', b'{}')]:
            path = self.source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        self.obj.compile()
        self.assertEqual(set(self.obj.files.values()),
                         {'Sound.bnk', 'Art/MapA/shared.png', 'Art/MapB/shared.png'})
        self.assertEqual(len(json.loads(Path(self.obj.modPath).read_text())), 3)
        self.assertEqual(self.events[-1][0], 'CompileModSourcesFinished')

    def test_save_failure_preserves_previous_output_and_metadata(self):
        Path(self.obj.modPath).write_bytes(b'previous good build')
        Package.fail_save = True
        with patch.object(traceback, 'print_exc'):
            self.obj.compile()
        self.assertEqual(Path(self.obj.modPath).read_bytes(), b'previous good build')
        self.assertEqual(self.obj.files, {'old': 'metadata'})
        self.assertEqual(self.events[-1][0], 'CompileModSourcesSaveError')
        self.assertTrue(Package.instances[0].closed)
        self.assertFalse(list(self.root.glob('.bmod-build-*')))
        self.assertFalse(self.obj._compile_lock.locked())

    def test_import_failure_closes_sprite_and_main_package(self):
        def fail(package, sprites):
            sprites.append(Package(self.root / 'sprite'))
            raise ValueError('bad sprite')
        self.obj._compileInto = fail
        with patch.object(traceback, 'print_exc'):
            self.obj.compile()
        self.assertTrue(all(package.closed for package in Package.instances))
        self.assertEqual(self.events[-1][0], 'CompileModSourcesSaveError')
        self.assertFalse(Path(self.obj.modPath).exists())

    def test_unknown_root_file_is_reported(self):
        (self.source / 'unknown.bin').write_bytes(b'unknown')
        self.obj.compile()
        self.assertIn(('CompileModSourcesUnknownFile', 'test', 'unknown.bin'), self.events)

    def test_concurrent_build_is_rejected_without_writing(self):
        with self.obj._compile_lock:
            self.obj.compile()
        self.assertEqual(self.events[-1][0], 'CompileModSourcesSaveError')
        self.assertFalse(Package.instances)

    def test_missing_sprite_file_fails_without_creating_empty_source(self):
        folder = self.source / 'Test.swf/sprites/DefineSprite_1_Test'
        folder.mkdir(parents=True)
        self.obj.compile.__globals__['BRAWLHALLA_SWFS'] = {'Test.swf': None}
        with patch.object(traceback, 'print_exc'):
            self.obj.compile()
        self.assertEqual(self.events[-1][0], 'CompileModSourcesSaveError')
        self.assertIn('frames.swf', self.events[-1][2])
        self.assertFalse((folder / 'frames.swf').exists())

    def test_invalid_language_text_does_not_fall_back_to_raw_binary(self):
        class InvalidLanguage:
            def FromTextFile(self, path):
                raise ValueError('invalid language text')
        folder = self.source / 'languages'
        folder.mkdir()
        (folder / 'language.1.txt').write_text('invalid')
        self.obj.compile.__globals__.update(LangFile=InvalidLanguage, MODLOADER_CACHE_PATH=str(self.root / 'cache'))
        with patch.object(traceback, 'print_exc'):
            self.obj.compile()
        self.assertEqual(self.events[-1][0], 'CompileModSourcesSaveError')
        self.assertIn('Cannot convert language file', self.events[-1][2])
        self.assertFalse(Path(self.obj.modPath).exists())

    def test_success_replaces_previous_output(self):
        Path(self.obj.modPath).write_bytes(b'previous')
        self.obj.compile()
        self.assertEqual(json.loads(Path(self.obj.modPath).read_text()), {})
        self.assertFalse(list(self.root.glob('.bmod-build-*')))

    @unittest.skipUnless(os.environ.get('CREATOR_JAVA_TESTS') == '1', 'Opt-in bundled Java integration test')
    def test_real_java_package_large_binary_roundtrip(self):
        with patch.dict(os.environ, {'APPDATA': str(self.root / 'appdata')}):
            from core.core import ffdec
            from core.core.swf.swf import Swf, GetElementId
        env = self.obj.compile.__globals__
        env.update(Swf=Swf, GetElementId=GetElementId)
        payload = bytes(range(256)) * (16 * 1024 * 1024 // 256)
        (self.source / 'Sound.bnk').write_bytes(payload)
        self.obj.compile()
        self.assertEqual(self.events[-1][0], 'CompileModSourcesFinished', self.events)
        package = Swf(self.obj.modPath)
        try:
            tag_id = next(key for key, name in self.obj.files.items() if name == 'Sound.bnk')
            self.assertEqual(package.exportBinaryData(elId=tag_id), payload)
        finally:
            package.close()


if __name__ == '__main__':
    unittest.main()
