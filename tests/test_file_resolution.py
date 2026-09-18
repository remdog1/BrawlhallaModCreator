import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def resolver(files):
    tree = ast.parse((ROOT / 'core/core/worker/brawlhalla.py').read_bytes())
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and
                 node.name in ('NormalizeGameFileKey', '_findGameFileKeyCaseInsensitive', 'ResolveBrawlhallaFileKey')]
    env = {'BRAWLHALLA_FILES': dict.fromkeys(files)}
    exec(compile(ast.Module(body=functions, type_ignores=[]), 'brawlhalla.py', 'exec'), env)
    return env['ResolveBrawlhallaFileKey']


class FileResolutionTests(unittest.TestCase):
    def test_thumbnail_folder_disambiguates_duplicate_basename(self):
        resolve = resolver(['images/thumbnails/MiamiDome.jpg', 'images/CupBackgrounds/MiamiDome.jpg'])
        self.assertEqual(resolve('thumbnails/miamidome.jpg'), 'images/thumbnails/MiamiDome.jpg')
        self.assertIsNone(resolve('MiamiDome.jpg'))

    def test_ambiguous_partial_path_is_not_guessed(self):
        resolve = resolver(['a/thumbnails/test.jpg', 'b/thumbnails/test.jpg'])
        self.assertIsNone(resolve('thumbnails/test.jpg'))
        self.assertEqual(resolve('a/thumbnails/test.jpg'), 'a/thumbnails/test.jpg')

    def test_legacy_unique_basename_still_resolves(self):
        resolve = resolver(['unique.jpg', 'images/unique.jpg'])
        self.assertEqual(resolve('export/unique.jpg'), 'unique.jpg')


if __name__ == '__main__':
    unittest.main()
