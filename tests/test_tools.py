import copy
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'benchmarks'))
sys.path.insert(0, str(ROOT / 'scripts'))
from compare import CONDITIONS, compare
from techdraw_bench import summary
from interactive_test import projection_snapshot
import apply_optimizations
from apply_optimizations import apply


class SummaryTests(unittest.TestCase):
    def test_percentiles_and_empty(self):
        self.assertEqual(summary([])['status'], 'unrun')
        self.assertEqual(summary([1, 4, 2, 3])['median_ms'], 2.5)
        self.assertEqual(summary(list(range(1, 101)))['p95_ms'], 95)

    def results(self):
        result = {key: 'same' for key in CONDITIONS}
        result.update(repeats=3, samples_ms={'zoom': [1., 2., 3.]})
        return result, copy.deepcopy(result)

    def test_matching_and_mismatched_conditions(self):
        a, b = self.results()
        self.assertIn('+0.0%', compare(a, b)[0][1])
        b['fixture_sha256'] = 'different'
        with self.assertRaisesRegex(ValueError, 'fixture_sha256'):
            compare(a, b)

    def test_failed_and_incomplete_measurements(self):
        a, b = self.results()
        b['samples_ms']['zoom'] = []
        self.assertIn('incomplete/skipped', compare(a, b)[0][1])
        b['restore_error'] = 'closed document'
        with self.assertRaisesRegex(ValueError, 'restore'):
            compare(a, b)

    def test_invalid_samples(self):
        a, b = self.results()
        b['samples_ms']['zoom'][0] = float('nan')
        with self.assertRaisesRegex(ValueError, 'Invalid timing'):
            compare(a, b)


class ProjectionSnapshotTests(unittest.TestCase):
    def test_groups_missing_geometry_and_cycles(self):
        def missing_edge(index):
            raise ValueError('projection pending')
        view = SimpleNamespace(Name='View', TypeId='TechDraw::DrawProjGroupItem',
                               State=['Up-to-date'], isDerivedFrom=lambda _: True,
                               getEdgeByIndex=lambda _: SimpleNamespace(isNull=lambda: False))
        section = SimpleNamespace(Name='Section', TypeId='TechDraw::DrawViewSection',
                                  State=['Up-to-date'], isDerivedFrom=lambda _: True,
                                  getEdgeByIndex=missing_edge)
        group = SimpleNamespace(Name='Group', Views=[view], isDerivedFrom=lambda _: False)
        group.Views.append(group)
        rows = projection_snapshot(SimpleNamespace(Views=[group, section, view]))
        self.assertEqual({row['name'] for row in rows}, {'View', 'Section'})
        by_name = {row['name']: row for row in rows}
        self.assertTrue(by_name['View']['first_edge_available'])
        self.assertFalse(by_name['Section']['first_edge_available'])
        self.assertIn('projection pending', by_name['Section']['edge_error'])


class PatchSafetyTests(unittest.TestCase):
    def check_patch_line_endings(self, trailing_space=False):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = root / 'source'
            repo.mkdir()
            def git(*args):
                return subprocess.check_output(['git', '-C', str(repo), *args])
            git('init', '-q')
            target = repo / 'edge.cpp'
            original = b'int before = 1;\n'
            target.write_bytes(original)
            git('add', 'edge.cpp')
            git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
                'commit', '-qm', 'fixture')
            commit = git('rev-parse', 'HEAD').decode().strip()
            updated = b'int after = 2;' + (b' ' if trailing_space else b'') + b'\n'
            target.write_bytes(updated)
            patch_bytes = git('diff', '--binary').replace(b'\n', b'\r\n')
            target.write_bytes(original)
            patch_file = root / 'windows.patch'
            patch_file.write_bytes(patch_bytes)
            with patch.object(apply_optimizations, 'UPSTREAM_COMMIT', commit), \
                    patch.object(apply_optimizations, 'PATCH', patch_file):
                if trailing_space:
                    with self.assertRaises(subprocess.CalledProcessError):
                        apply(repo)
                    self.assertEqual(target.read_bytes(), original)
                else:
                    apply(repo, check_only=True)
                    self.assertEqual(target.read_bytes(), original)
                    apply(repo)
                    self.assertEqual(target.read_bytes(), updated)
                    self.assertEqual(git('diff', '--check'), b'')

    def test_crlf_patch_applies_to_lf_source(self):
        self.check_patch_line_endings()

    def test_crlf_normalization_keeps_whitespace_validation(self):
        self.check_patch_line_endings(trailing_space=True)

    def test_wrong_commit_is_not_modified(self):
        with tempfile.TemporaryDirectory() as directory:
            subprocess.run(['git', 'init', '-q', directory], check=True)
            subprocess.run(['git', '-C', directory, '-c', 'user.name=Test', '-c',
                            'user.email=test@example.invalid', 'commit', '--allow-empty', '-qm', 'fixture'], check=True)
            sentinel = Path(directory) / 'untracked-work.txt'
            sentinel.write_text('preserve me')
            with self.assertRaisesRegex(RuntimeError, 'verified'):
                apply(directory)
            self.assertEqual(sentinel.read_text(), 'preserve me')
            self.assertEqual(subprocess.check_output(['git', '-C', directory, 'diff']), b'')


if __name__ == '__main__':
    unittest.main()
