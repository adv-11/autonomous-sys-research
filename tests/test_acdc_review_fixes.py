"""Synthetic regressions for GPT's formal review of Claude's ACDC adapter."""

import copy
import io
import json
import struct
import tempfile
import unittest
import zlib
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

import test_acdc as fixtures
from threshold_transfer import acdc as A
from threshold_transfer.data import PreflightError


def chunk(kind, body):
    return struct.pack('>I', len(body)) + kind + body + struct.pack('>I', zlib.crc32(kind + body))


def tiny_png(*, width=2, height=1, compressed=None):
    header = chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 0, 0, 0, 0))
    payload = zlib.compress(b'\x00\x00\x01') if compressed is None else compressed
    return b'\x89PNG\r\n\x1a\n' + header + chunk(b'IDAT', payload) + chunk(b'IEND', b'')


class NativeBoundaryTests(unittest.TestCase):
    def test_malformed_collections_cannot_become_empty_lists(self):
        for key in ('images', 'annotations', 'categories'):
            for value in ({}, None, 1, True, '', [None], [[]]):
                with self.subTest(key=key, value=value):
                    doc = fixtures.adverse_doc()
                    doc[key] = value
                    with self.assertRaises(PreflightError):
                        fixtures.convert(doc)
        doc = fixtures.adverse_doc()
        doc['annotations'] = []
        self.assertEqual(len(fixtures.convert(doc)['images']), 3)
        doc['images'] = []
        self.assertEqual(fixtures.convert(doc)['images'], [])

    def test_native_integer_types_reject_numeric_aliases_and_containers(self):
        for field in ('category_id', 'iscrowd', 'image_id'):
            original = fixtures.adverse_doc()['annotations'][0][field]
            for value in (float(original), True, [], {}):
                with self.subTest(field=field, value=value):
                    doc = fixtures.adverse_doc()
                    doc['annotations'][0][field] = value
                    with self.assertRaises(PreflightError):
                        fixtures.convert(doc)
        for value in (24.0, True, [], {}):
            doc = fixtures.adverse_doc()
            doc['categories'][0]['id'] = value
            with self.subTest(category_table_id=value), self.assertRaises(PreflightError):
                fixtures.convert(doc)
        for size in ([8.0, 10], [8, 10.0], [True, 10], {}, None):
            doc = fixtures.adverse_doc()
            doc['annotations'][0]['segmentation']['size'] = size
            with self.subTest(size=size), self.assertRaises(PreflightError):
                fixtures.convert(doc)

    def test_filename_rejects_final_newline(self):
        doc = fixtures.adverse_doc()
        doc['images'][0]['file_name'] += '\n'
        doc['images'][0]['segm_file'] += '\n'
        with self.assertRaises(PreflightError):
            fixtures.convert(doc)

    def test_condition_certification_checks_duplicates_and_categories(self):
        aggregate = fixtures.adverse_doc()
        part = copy.deepcopy(aggregate)
        part['images'] = part['images'][:2]
        for key in ('images', 'annotations'):
            damaged = copy.deepcopy(part)
            damaged[key].append(copy.deepcopy(damaged[key][0]))
            with self.subTest(key=key), self.assertRaises(PreflightError):
                A.condition_file_check(aggregate, damaged, 'fog')
        part['categories'][0]['name'] = 'changed'
        with self.assertRaises(PreflightError):
            A.condition_file_check(aggregate, part, 'fog')

    def test_cli_malformed_native_input_preserves_existing_output(self):
        helper = fixtures.CliTests('test_inventory_and_convert')
        with tempfile.TemporaryDirectory() as tmp:
            root = helper._root(tmp)
            source = root / A.AGGREGATE_FILES[('train', False)]
            out = Path(tmp) / 'result.json'
            for value in ({}, None, 1):
                doc = fixtures.adverse_doc()
                doc['annotations'] = value
                source.write_text(json.dumps(doc), encoding='utf8')
                out.write_bytes(b'previous result')
                for argv in (['inventory', '--root', str(root), '--out', str(out)],
                             ['convert', '--root', str(root), '--split', 'train', '--ignore-policy',
                              'no_ignore_declared', '--out', str(out)]):
                    with self.subTest(value=value, command=argv[0]):
                        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                            self.assertEqual(A.main(argv), 2)
                        self.assertEqual(out.read_bytes(), b'previous result')

    def test_panoptic_malformed_collections_fail_closed(self):
        doc = fixtures.adverse_doc()
        original = {'images': [{'id': 'frame', 'file_name': doc['images'][0]['file_name']}],
                    'annotations': [{'image_id': 'frame', 'segments_info': []}]}
        for key in ('images', 'annotations', 'segments_info'):
            for value in ({}, None, 1, [None]):
                damaged = copy.deepcopy(original)
                target = damaged['annotations'][0] if key == 'segments_info' else damaged
                target[key] = value
                with self.subTest(key=key, value=value), self.assertRaises(PreflightError):
                    A.panoptic_crosscheck(fixtures.convert(), damaged)


class PngBoundaryTests(unittest.TestCase):
    def check_bad(self, data):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'mask.png'
            path.write_bytes(data)
            with self.assertRaises(PreflightError):
                A.read_png_gray8(path)

    def test_every_truncated_prefix_fails_through_preflight_error(self):
        data = tiny_png()
        for length in range(len(data)):
            with self.subTest(length=length):
                self.check_bad(data[:length])

    def test_chunk_structure_and_dimensions(self):
        data = tiny_png()
        for damaged in (data[:33] + data[8:33] + data[33:],  # duplicate header
                        data[:33] + chunk(b'ABCD', b'') + data[33:],
                        data[:33] + chunk(b'abcd', b'') + data[33:],  # reserved bit
                        data + b'junk', tiny_png(width=0), tiny_png(height=0),
                        tiny_png(width=0x80000000), data[:8] + data[33:],
                        data[:33] + chunk(b'IEND', b''),
                        data[:-12] + chunk(b'IEND', b'nonempty')):
            with self.subTest(damaged=damaged):
                self.check_bad(damaged)

    def test_bad_incomplete_and_extra_zlib_streams(self):
        good = zlib.compress(b'\x00\x00\x01')
        for compressed in (b'bad', good[:-1], good + b'extra', good + good,
                           zlib.compress(b'\x00' * 10000), zlib.compress(b'')):
            with self.subTest(compressed=compressed[:15]):
                self.check_bad(tiny_png(compressed=compressed))

    def test_consecutive_idat_and_ancillary_chunk_order(self):
        data = tiny_png()
        payload = zlib.compress(b'\x00\x00\x01')
        split = chunk(b'IDAT', payload[:3]) + chunk(b'IDAT', payload[3:])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'mask.png'
            path.write_bytes(data[:33] + split + data[-12:])
            self.assertEqual(A.read_png_gray8(path), (2, 1, b'\x00\x01'))
            path.write_bytes(data[:33] + chunk(b'tEXt', b'k\x00v') + split + data[-12:])
            self.assertEqual(A.read_png_gray8(path), (2, 1, b'\x00\x01'))
        separated = chunk(b'IDAT', payload[:3]) + chunk(b'tEXt', b'k\x00v') + chunk(b'IDAT', payload[3:])
        self.check_bad(data[:33] + separated + data[-12:])

    def test_resource_limits_are_enforced_before_inflation(self):
        with patch.object(A, 'MAX_MASK_PIXELS', 1):
            self.check_bad(tiny_png())
        with patch.object(A, 'MAX_MASK_PNG_BYTES', 20):
            self.check_bad(tiny_png())

    def test_cli_corrupt_mask_preserves_existing_output(self):
        helper = fixtures.CliTests('test_inventory_and_convert')
        with tempfile.TemporaryDirectory() as tmp:
            root = helper._root(tmp)
            for image in fixtures.adverse_doc()['images']:
                path = root / 'gt_trainval/gt' / image['segm_file'].replace('_gt_labelIds', '_gt_invIds')
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(tiny_png(compressed=b'bad'))
            out = Path(tmp) / 'result.json'
            out.write_bytes(b'previous result')
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                self.assertEqual(A.main(['inventory', '--root', str(root), '--invalid-images', '1',
                                         '--out', str(out)]), 2)
            self.assertEqual(out.read_bytes(), b'previous result')


if __name__ == '__main__':
    unittest.main()
