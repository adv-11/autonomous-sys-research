"""Single-use, CPU-only NightOwls access pilot. GPT Sol, 2026-11-13.

Historical stopped attempt; execution is disabled pending reviewed supervision
and renewed explicit authorization. --selftest makes no network requests.
No resume, retries, inference, or archive fallback. Private paths are canonical.
"""
import argparse
import collections
import datetime as dt
import hashlib
import http.client
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile

ROOT = Path('C:/Users/Advait/autonomous-sys-research')
DEST = ROOT / 'data/nightowls/image_access_pilot/2026-11-13'
URL = 'https://thor.robots.ox.ac.uk/nightowls/python/nightowls_validation.zip'
DEADLINE = dt.datetime(2026, 11, 13, 20, 9, tzinfo=dt.timezone.utc).timestamp()
SELECTION_HASH = '4f31e685cd3d2d263448e7faf207d80f7befe8c6738b041c3bc4d6614b5de99a'
ANNOTATION_HASH = '584c0dc11f0d086fc5bcbaca0385cf2dd9794074f815f2727fbf9a093fd9a9b6'
TOTAL_CAP = 150_000_000
INDEX_CAP = 16_000_000
EXECUTION_AUTHORIZED = False


class Stop(Exception):
    pass


def require_execution_authorization():
    if not EXECUTION_AUTHORIZED:
        raise Stop('stopped_pilot_no_renewed_execution_authorization')


def worker_command(script_path=None):
    """Proposed correction: direct base interpreter, not a venv redirector.

    A parent-PID check runs before the target script. Site-package paths retain
    the existing Pillow installation without installing or importing GPU code.
    This builder does not authorize execution of the stopped access pilot.
    """
    base = getattr(sys, '_base_executable', None)
    if not base or not Path(base).is_file():
        raise Stop('base_interpreter_unavailable')
    target = str(Path(script_path or __file__).resolve())
    packages = [path for path in sys.path if Path(path).name == 'site-packages']
    bootstrap = ('import os,runpy,sys;'
                 f'assert os.getppid()=={os.getpid()}, "unexpected_worker_parent";'
                 f'sys.path[:0]={packages!r};'
                 f'sys.argv=[{target!r}, "--worker"];'
                 f'runpy.run_path({target!r},run_name="__main__")')
    return [str(Path(base).resolve()), '-I', '-B', '-c', bootstrap]


def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def atomic(path, value):
    tmp = path.with_suffix(path.suffix + '.tmp')
    with tmp.open('w', encoding='utf-8') as out:
        json.dump(value, out, indent=2, allow_nan=False)
        out.flush()
        os.fsync(out.fileno())
    os.replace(tmp, path)


def check_time():
    if time.time() >= DEADLINE:
        raise Stop('absolute_deadline')


def reserve(state, length, phase):
    check_time()
    if length <= 0 or state['charged_bytes'] + length > TOTAL_CAP:
        raise Stop('total_byte_cap')
    if phase == 'index' and state['index_charged_bytes'] + length > INDEX_CAP:
        raise Stop('index_byte_cap')
    state['charged_bytes'] += length
    if phase == 'index':
        state['index_charged_bytes'] += length


def validate_response(response, start, end, suffix, identity):
    if response.status != 206:
        raise Stop('non_206')
    if response.geturl() != URL:
        raise Stop('unexpected_response_url')
    match = re.fullmatch(r'bytes (\d+)-(\d+)/(\d+)', response.headers.get('Content-Range', ''))
    if not match:
        raise Stop('missing_or_invalid_content_range')
    first, last, total = map(int, match.groups())
    expected = (max(0, total - suffix), total - 1) if suffix else (start, end)
    if (first, last) != expected or not (0 <= first <= last < total):
        raise Stop('mismatched_content_range')
    if identity.get('total') is not None and identity['total'] != total:
        raise Stop('archive_total_changed')
    encoding = response.headers.get('Content-Encoding', 'identity')
    if encoding.lower() != 'identity':
        raise Stop('unexpected_content_encoding')
    content_length = response.headers.get('Content-Length')
    if content_length is not None and content_length != str(last - first + 1):
        raise Stop('mismatched_content_length')
    updates = {'total': total}
    for key in ('ETag', 'Last-Modified'):
        value = response.headers.get(key)
        if key in identity and identity[key] != value:
            raise Stop('archive_validator_changed')
        if value is not None:
            updates[key] = value
    identity.update(updates)
    return first, last


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def http_error_302(self, request, response, code, message, headers):
        response.close()
        raise Stop('redirect_refused_before_body')
    http_error_301 = http_error_303 = http_error_307 = http_error_308 = http_error_302


class Transport:
    def __init__(self, state):
        self.state = state
        self.opener = urllib.request.build_opener(NoRedirect())
        self.events = (DEST / 'logs/requests.jsonl').open('x', encoding='utf-8')

    def checkpoint(self):
        atomic(DEST / 'logs/status.json', self.state)

    def event(self, kind, **fields):
        self.events.write(json.dumps({'utc': utc(), 'event': kind, **fields}) + '\n')
        self.events.flush()
        os.fsync(self.events.fileno())

    def fetch(self, start=None, length=None, suffix=None, phase='index'):
        expected = suffix if suffix else length
        reserve(self.state, expected, phase)
        self.state['requests_reserved'] += 1
        number = self.state['requests_reserved']
        end = start + length - 1 if suffix is None else None
        requested = f'bytes=-{suffix}' if suffix else f'bytes={start}-{end}'
        self.state['active_request'] = {'number': number, 'range': requested, 'phase': phase, 'reserved': expected}
        self.checkpoint()
        self.event('reserved_before_request', **self.state['active_request'], charged_bytes=self.state['charged_bytes'])
        request = urllib.request.Request(URL, headers={'Range': requested, 'Accept-Encoding': 'identity', 'User-Agent': 'NightOwls-authorized-private-access-pilot/1'})
        response = None
        chunks = []
        try:
            check_time()
            response = self.opener.open(request, timeout=max(0.01, min(30, DEADLINE - time.time())))
            self.event('headers_before_body', number=number, status=response.status, url=response.geturl(), headers=dict(response.headers.items()), prior_identity=dict(self.state['identity']))
            first, last = validate_response(response, start, end, suffix, self.state['identity'])
            self.checkpoint()
            self.event('identity_accepted_before_body', number=number, identity=self.state['identity'])
            remaining = last - first + 1
            while remaining:
                check_time()
                try:
                    part = response.read(min(65536, remaining))
                except http.client.IncompleteRead as error:
                    self.state['confirmed_bytes'] += len(error.partial)
                    if phase == 'index':
                        self.state['index_confirmed_bytes'] += len(error.partial)
                    self.checkpoint()
                    raise
                if not part:
                    raise Stop('short_body')
                self.state['confirmed_bytes'] += len(part)
                if phase == 'index':
                    self.state['index_confirmed_bytes'] += len(part)
                chunks.append(part)
                remaining -= len(part)
                self.checkpoint()
            check_time()
            body = b''.join(chunks)
            self.event('body_complete', number=number, confirmed_body_bytes=len(body), confirmed_total=self.state['confirmed_bytes'], charged_total=self.state['charged_bytes'], identity=self.state['identity'])
            if phase == 'index':
                with (DEST / f'archive_index/range_{number:04d}.bin').open('xb') as out:
                    out.write(body)
            self.state['requests_completed'] += 1
            self.state['active_request'] = None
            self.checkpoint()
            return first, body
        except BaseException as error:
            # HTTPError carries an unread body. Never ask urllib to consume it.
            if isinstance(error, urllib.error.HTTPError):
                self.event('http_error_before_body', number=number, status=error.code, headers=dict(error.headers.items()))
                error.close()
            self.event('request_failed', number=number, error_type=type(error).__name__, error=str(error), confirmed_total=self.state['confirmed_bytes'], charged_total=self.state['charged_bytes'])
            raise
        finally:
            if response is not None:
                response.close()


class RangeFile:
    def __init__(self, transport, first, tail):
        self.transport = transport
        self.size = transport.state['identity']['total']
        self.pos = 0
        self.cache = [(first, tail)]
        self.phase = 'index'

    def seekable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, offset, whence=0):
        target = offset if whence == 0 else self.pos + offset if whence == 1 else self.size + offset if whence == 2 else -1
        if not 0 <= target <= self.size:
            raise Stop('invalid_archive_seek')
        self.pos = target
        return target

    def read(self, length=-1):
        check_time()
        if length < 0:
            # ZipFile uses read() for EOCD tails. Never permit whole-file reads.
            length = self.size - self.pos
            if length > 65557:
                raise Stop('unbounded_archive_read')
        length = min(length, self.size - self.pos)
        if length == 0:
            return b''
        if length > (INDEX_CAP if self.phase == 'index' else 3_000_000):
            raise Stop('oversized_archive_read')
        for first, body in self.cache:
            if first <= self.pos and self.pos + length <= first + len(body):
                result = body[self.pos - first:self.pos - first + length]
                self.pos += length
                return result
        first, result = self.transport.fetch(self.pos, length, phase=self.phase)
        if self.phase == 'index':
            self.cache.append((first, result))
        self.pos += len(result)
        return result


def safe_name(name):
    path = PurePosixPath(name)
    if not name or '\\' in name or ':' in name or '\x00' in name or path.is_absolute() or any(x in ('', '.', '..') for x in name.split('/')):
        raise Stop('unsafe_member_name')


def read_inputs():
    selection = (ROOT / 'outputs/nightowls_image_access_pilot_20261113/selection.json').read_bytes()
    annotations = (ROOT / 'data/nightowls/annotations/nightowls_validation.json').read_bytes()
    if hashlib.sha256(selection).hexdigest() != SELECTION_HASH or hashlib.sha256(annotations).hexdigest() != ANNOTATION_HASH:
        raise Stop('private_input_hash_mismatch')
    records = json.loads(selection)['images']
    native = {x['id']: x for x in json.loads(annotations)['images']}
    if len(records) != 64 or len({x['id'] for x in records}) != 64 or len({x['file_name'] for x in records}) != 64:
        raise Stop('selection_count_or_uniqueness')
    buckets = collections.Counter(x['recordings_id'] for x in records)
    if buckets[None] != 14 or sorted(v for k, v in buckets.items() if k is not None) != [10] * 5:
        raise Stop('selection_buckets')
    for record in records:
        if record != native[record['id']] or record['daytime'] != 'night' or (record['width'], record['height']) != (1024, 640):
            raise Stop('selection_native_metadata')
        safe_name(record['file_name'])
    return records


def worker():
    require_execution_authorization()
    # The controller has durably recorded its PID and timeout before launch.
    state = {'status': 'STARTING', 'worker_pid': os.getpid(), 'started_utc': utc(), 'identity': {}, 'completed': 0, 'planned': 64, 'charged_bytes': 0, 'confirmed_bytes': 0, 'index_charged_bytes': 0, 'index_confirmed_bytes': 0, 'requests_reserved': 0, 'requests_completed': 0, 'active_request': None, 'images': []}
    transport = Transport(state)
    started = time.monotonic()
    try:
        records = read_inputs()
        from PIL import Image
        Image.MAX_IMAGE_PIXELS = 1024 * 640
        state['status'] = 'INDEX'
        transport.checkpoint()
        first, tail = transport.fetch(suffix=65557)
        archive_file = RangeFile(transport, first, tail)
        with zipfile.ZipFile(archive_file, mode='r', allowZip64=True) as archive:
            mapping = collections.defaultdict(list)
            for info in archive.infolist():
                mapping[info.filename].append(info)
            selected = []
            # Validate the complete fixed mapping and bounds before any image.
            for record in records:
                candidates = mapping[record['file_name']] + mapping['nightowls_validation/' + record['file_name']]
                if len(candidates) != 1:
                    raise Stop('member_mapping_not_exactly_one')
                info = candidates[0]
                safe_name(info.filename)
                if info.is_dir() or info.flag_bits & 1 or not info.filename.lower().endswith('.png'):
                    raise Stop('member_type_or_encryption')
                maximum = record['width'] * record['height'] * 4 + 65536
                if not 0 < info.file_size <= maximum or not 0 < info.compress_size <= maximum:
                    raise Stop('member_size_bound')
                selected.append((record, info))
            state['mapping_validated'] = len(selected)
            state['archive_member_count'] = len(archive.infolist())
            archive_file.phase = 'image'
            state['status'] = 'IMAGES'
            transport.checkpoint()
            for ordinal, (record, info) in enumerate(selected, 1):
                check_time()
                began = time.monotonic()
                # ZipFile enforces local-name consistency and CRC on full read.
                payload = archive.read(info)
                if len(payload) != info.file_size or not payload.startswith(b'\x89PNG\r\n\x1a\n'):
                    raise Stop('png_signature_or_size')
                with Image.open(io.BytesIO(payload)) as image:
                    if image.format != 'PNG' or image.size != (record['width'], record['height']):
                        raise Stop('png_format_or_dimensions')
                    mode = image.mode
                    image.verify()
                with Image.open(io.BytesIO(payload)) as image:
                    image.load()
                    if image.size != (1024, 640) or image.mode != mode:
                        raise Stop('png_load_metadata')
                check_time()
                digest = hashlib.sha256(payload).hexdigest()
                target = DEST / f'images/{ordinal:03d}.png'
                with target.open('xb') as out:
                    out.write(payload)
                    out.flush()
                    os.fsync(out.fileno())
                state['images'].append({'ordinal': ordinal, 'native_id': record['id'], 'native_file_name': record['file_name'], 'member': info.filename, 'sha256': digest, 'crc32': f'{info.CRC:08x}', 'bytes': len(payload), 'shape': [640, 1024], 'mode': mode, 'zip_crc_passed': True, 'pillow_verify_passed': True, 'pillow_load_passed': True, 'seconds': time.monotonic() - began})
                state['completed'] = ordinal
                transport.checkpoint()
                if ordinal % 8 == 0:
                    print(json.dumps({'milestone_images': ordinal, 'confirmed_bytes': state['confirmed_bytes'], 'charged_bytes': state['charged_bytes'], 'remaining_seconds': max(0, DEADLINE - time.time())}), flush=True)
        state['status'] = 'COMPLETED'
        state['error'] = None
        return_code = 0
    except BaseException as error:
        state['status'] = 'STOPPED'
        state['error'] = {'type': type(error).__name__, 'message': str(error)}
        return_code = 1
        print(json.dumps({'technical_failure': type(error).__name__, 'reason': str(error), 'completed': state['completed'], 'confirmed_bytes': state['confirmed_bytes'], 'charged_bytes': state['charged_bytes']}), flush=True)
    finally:
        state['ended_utc'] = utc()
        state['wall_seconds'] = time.monotonic() - started
        state['cpu_seconds'] = time.process_time()
        transport.checkpoint()
        transport.events.close()
    return return_code


def controller():
    require_execution_authorization()
    check_time()
    # Refuse even an empty prior destination: no silent resume or overwritten run.
    DEST.mkdir(parents=True, exist_ok=False)
    for folder in ('images', 'logs', 'archive_index'):
        (DEST / folder).mkdir()
    control = {'status': 'STARTING', 'control_pid': os.getpid(), 'started_utc': utc(), 'absolute_stop_utc': '2026-11-13T20:09:00Z', 'timeout_seconds': min(1800, DEADLINE - time.time()), 'worker_exit_verified': False}
    control_path = DEST / 'logs/control.json'
    atomic(control_path, control)
    process = None
    try:
        with (DEST / 'logs/worker_stdout.jsonl').open('x', encoding='utf-8') as stdout, (DEST / 'logs/worker_stderr.txt').open('x', encoding='utf-8') as stderr:
            process = subprocess.Popen(worker_command(), stdout=stdout, stderr=stderr, stdin=subprocess.DEVNULL)
            control.update(status='WATCHING', worker_pid=process.pid)
            atomic(control_path, control)
            try:
                # Leave a one-second margin for kill/reap before the UTC stop.
                process.wait(timeout=max(0, min(control['timeout_seconds'], DEADLINE - time.time()) - 1))
                control['status'] = 'WORKER_EXITED'
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
                control['status'] = 'WATCHDOG_KILLED'
    finally:
        if process is not None:
            if process.poll() is None:
                process.kill()
                process.wait()
            control['worker_returncode'] = process.returncode
            control['worker_exit_verified'] = process.poll() is not None
        control['ended_utc'] = utc()
        atomic(control_path, control)
    print(json.dumps(control), flush=True)
    return 0 if control.get('worker_returncode') == 0 else 1


def selftest():
    from unittest.mock import patch
    class Response:
        status = 206
        headers = {'Content-Range': 'bytes 10-19/100', 'Content-Length': '10', 'ETag': 'fixed'}
        reads = 0
        def geturl(self):
            return URL
        def read(self, *args):
            self.reads += 1
            raise AssertionError('body must not be read')
    passed = []
    for label, status, headers, identity in (
        ('non206', 200, Response.headers, {}),
        ('mismatched_range', 206, {**Response.headers, 'Content-Range': 'bytes 11-20/100'}, {}),
        ('missing_range', 206, {}, {}),
        ('identity_change', 206, Response.headers, {'total': 100, 'ETag': 'other'}),
        ('total_change', 206, Response.headers, {'total': 101}),
    ):
        response = Response()
        response.status, response.headers = status, headers
        try:
            validate_response(response, 10, 19, None, identity)
        except Stop:
            assert response.reads == 0
            passed.append(label)
        else:
            raise AssertionError(label)
    for label, state, phase in (
        ('total_cap', {'charged_bytes': TOTAL_CAP, 'index_charged_bytes': 0}, 'image'),
        ('index_cap', {'charged_bytes': INDEX_CAP, 'index_charged_bytes': INDEX_CAP}, 'index'),
    ):
        before = dict(state)
        try:
            # These are synthetic cap tests, independent of the expired run's
            # historical wall-clock deadline.
            with patch.dict(globals(), {'DEADLINE': float('inf')}):
                reserve(state, 1, phase)
        except Stop as error:
            assert str(error) == ('total_byte_cap' if label == 'total_cap' else 'index_byte_cap')
            assert state == before
            passed.append(label)
        else:
            raise AssertionError(label)
    print(json.dumps({'synthetic_protective_checks_passed': passed, 'network_requests': 0}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--selftest', action='store_true')
    mode.add_argument('--execute', action='store_true')
    mode.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.selftest:
        selftest()
    else:
        sys.exit(worker() if args.worker else controller())
