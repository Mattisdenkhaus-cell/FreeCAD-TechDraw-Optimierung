#!/usr/bin/env python3
"""Compare GUI-step results only when their recorded test conditions match."""
import argparse
import json
from pathlib import Path
from techdraw_bench import summary

CONDITIONS = ('schema', 'fixture_sha256', 'page', 'view', 'edge', 'dimension',
              'viewport_px', 'device_pixel_ratio', 'initial_transform', 'initial_scroll',
              'warmup', 'repeats', 'fixture_kind', 'renderer_note', 'platform', 'qt', 'metric')


def compare(before, after):
    for result in (before, after):
        if result.get('error') or result.get('restore_error'):
            raise ValueError('A benchmark failed or could not restore state; results are not comparable.')
    mismatches = [key for key in CONDITIONS if key not in before or key not in after or before[key] != after[key]]
    # Direct selection diagnostics and copied-document tests have different GUI work.
    if before.get('copy_mode') != after.get('copy_mode'):
        mismatches.append('copy_mode')
    for key in ('navigation_preview_preference', 'partial_viewport_updates_preference',
                'viewport_class', 'viewport_update_mode', 'open_document_count',
                'document_object_count', 'page_view_count'):
        if before.get('diagnostics', {}).get(key) != after.get('diagnostics', {}).get(key):
            mismatches.append('diagnostics.' + key)
    if mismatches:
        raise ValueError('Different or missing conditions: ' + ', '.join(mismatches))
    rows = []
    for name in before['samples_ms']:
        a, b = before['samples_ms'][name], after['samples_ms'].get(name, [])
        if len(a) != before['repeats'] or len(b) != after['repeats']:
            rows.append((name, 'incomplete/skipped; no speed claim'))
            continue
        if any(not isinstance(x, (int, float)) or not 0 <= x < float('inf') for x in a + b):
            raise ValueError('Invalid timing samples.')
        sa, sb = summary(a), summary(b)
        if sa['median_ms'] == 0:
            raise ValueError('Zero baseline median cannot support a relative comparison.')
        change = (sb['median_ms'] / sa['median_ms'] - 1) * 100
        rows.append((name, f"median {sa['median_ms']:.3f} -> {sb['median_ms']:.3f} ms ({change:+.1f}%); "
                          f"p95 {sa['p95_ms']:.3f} -> {sb['p95_ms']:.3f} ms"))
    return rows


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('baseline', type=Path)
    parser.add_argument('optimized', type=Path)
    args = parser.parse_args()
    try:
        for name, result in compare(json.loads(args.baseline.read_text()), json.loads(args.optimized.read_text())):
            print(f'{name}: {result}')
    except ValueError as error:
        parser.exit(1, f'{error}\n')
