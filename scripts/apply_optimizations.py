#!/usr/bin/env python3
"""Apply the combined, reviewable C++ patch to an exact, clean FreeCAD checkout."""
import argparse
from pathlib import Path
import subprocess

UPSTREAM_COMMIT = '4fd3bf320d9566a27e60069fc8387448aaa3a094'
PATCH = Path(__file__).resolve().parents[1] / 'patches/FreeCAD-1.1.4-TechDraw-performance.patch'


def apply(source, check_only=False):
    source = Path(source).resolve()
    def git(*args):
        return subprocess.run(['git', '-C', str(source), *args], check=True,
                              text=True, capture_output=True).stdout.strip()
    if git('rev-parse', 'HEAD') != UPSTREAM_COMMIT:
        raise RuntimeError('Refusing to patch: checkout is not the verified FreeCAD 1.1.4 commit.')
    if git('status', '--porcelain', '--untracked-files=normal'):
        raise RuntimeError('Refusing to patch a modified checkout; preserve changes and use a clean source copy.')
    git('apply', '--check', '--whitespace=error-all', str(PATCH))
    if not check_only:
        git('apply', '--whitespace=error-all', str(PATCH))
        git('diff', '--check')
    print(f'PASS: {"checked" if check_only else "applied"} combined patch at {UPSTREAM_COMMIT}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    try:
        apply(args.source, args.check)
    except (RuntimeError, subprocess.CalledProcessError) as error:
        parser.exit(1, f'{error}\n{getattr(error, "stderr", "")}')
