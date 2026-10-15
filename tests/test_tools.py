import copy
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'benchmarks'))
sys.path.insert(0, str(ROOT / 'scripts'))
from compare import CONDITIONS, compare
from techdraw_bench import summary
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


class PatchSafetyTests(unittest.TestCase):
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
