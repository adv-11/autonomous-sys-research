"""CPU-only regressions: reviewed prototypes cannot launch or approve GPU work."""

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


def module(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / file)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


K = module('pilot_hold_kitti', 'scripts/pilot/kitti_pilot.py')
A = module('pilot_hold_audit', 'scripts/pilot/near_duplicate_audit.py')


class ReviewHoldTests(unittest.TestCase):
    def test_capture_and_summary_stop_before_config_or_gpu(self):
        for mode in ('capture', 'summarize'):
            with self.subTest(mode=mode), mock.patch.object(K, '_paths') as paths, \
                    mock.patch.object(K, 'gpu_preflight') as gpu:
                with self.assertRaisesRegex(SystemExit, 'DISABLED'):
                    K.main([mode, '--config', 'does-not-exist.json'])
                paths.assert_not_called()
                gpu.assert_not_called()

    def test_direct_capture_entries_are_also_disabled(self):
        with self.assertRaisesRegex(SystemExit, 'DISABLED'):
            K.capture_ultralytics(None, None, None, None, None)
        with self.assertRaisesRegex(SystemExit, 'DISABLED'):
            K.capture_rtdetr(None, None, None, None)

    def test_pass_record_cannot_approve_grid(self):
        for record in ({'pipeline': 'synthetic', 'status': 'PASS'},
                       {'pipeline': 'synthetic', 'status': 'PASS', 'checkpoint_sha256_verified': False}):
            _, result = K.summarize_capture(record, {})
            self.assertFalse(result['derivation_supported'])
            self.assertTrue(result['grid'].startswith('UNSUPPORTED'))

    def test_audit_cli_does_not_reuse_or_overwrite_unbound_cache(self):
        for mode in ('hash', 'screen', 'summarize'):
            with self.subTest(mode=mode), mock.patch.object(A, '_cfg') as cfg:
                with self.assertRaisesRegex(SystemExit, 'DISABLED'):
                    A.main([mode, '--config', 'does-not-exist.json'])
                cfg.assert_not_called()

    def test_selection_output_cannot_escape_private_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'config.json'
            for value in ('../elsewhere', str(Path(tmp).resolve())):
                p.write_text(json.dumps({'private_output_dir': value}), encoding='utf8')
                with self.subTest(value=value), self.assertRaises(SystemExit):
                    K._paths(p)


if __name__ == '__main__':
    unittest.main()
