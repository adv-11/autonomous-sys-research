"""GPT Sol: experiment-specific Colab controller and independent stop process.

CPU/stdlib only on Windows. A separate guard is started BEFORE allocation.
No new sessions, retries or recipe choices are made after a failed stage.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import time

HERE = Path(__file__).resolve().parent
ROOT = Path('C:/Users/Advait/autonomous-sys-research')
OUT = ROOT / 'outputs/rtdetr_transfer_20261123'
STATE = OUT / 'live_state.json'
SESSION = 'rtdetr1123'
CLI = str(Path.home() / '.local/bin/colab.exe')
CLI_PYTHON = str(Path.home() / 'AppData/Roaming/uv/tools/google-colab-cli/Scripts/python.exe')


def orphan_endpoints(release=False):
    """Official CLI-client recovery for a request that never saved its alias.

    Admission established zero assignments and this task is the sole operator.
    Only endpoints observed during THIS allocation request are releasable.
    No credentials or runtime-proxy tokens are returned.
    """
    record = OUT / 'owned_endpoints.json'
    script = ('import json\nfrom colab_cli.common import state\n'
              + (f'endpoints=json.loads({str(record)!r} and open({str(record)!r}).read())\n'
                 'for endpoint in endpoints: state.client.unassign(endpoint)\n'
                 'print(json.dumps(endpoints))\n' if release else
                 'print(json.dumps([a.endpoint for a in state.client.list_assignments()]))\n'))
    result = subprocess.run([CLI_PYTHON, '-c', script], capture_output=True, text=True, timeout=45, check=True)
    endpoints = json.loads(result.stdout)
    if not release:
        record.write_text(json.dumps(endpoints))
    return endpoints


def write_state(value):
    temp = STATE.with_suffix('.tmp')
    temp.write_text(json.dumps(value, indent=2))
    temp.replace(STATE)


def cli(args, log, timeout=None):
    with (OUT / log).open('a', encoding='utf-8') as stream:
        process = subprocess.Popen([CLI, *args], stdout=stream, stderr=subprocess.STDOUT,
                                   encoding='utf-8', env={**os.environ, 'COLAB_CLI_ASSIGN_RETRIES': '0',
                                                         'COLAB_CLI_REQUEST_TIMEOUT': '480'})
        try:
            result = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            # The Windows console launcher creates Python descendants. Stop the
            # entire owned process tree before releasing an uncertain assignment.
            subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], stdout=stream, stderr=stream)
            raise
    if result:
        raise RuntimeError(f'colab {args[0]} failed ({result}); see {log}')


def guard():
    """Independently releases this session even if the LLM/controller disappears."""
    while True:
        state = json.loads(STATE.read_text())
        if state.get('teardown_verified'):
            return
        if state['status'] == 'ALLOCATING':
            try:
                orphan_endpoints()
            except Exception:
                pass  # Primary stop still runs at the hard deadline.
        if time.time() >= state['hard_deadline_unix']:
            # Stop has its own bounded retry, not another training attempt.
            for attempt in range(2):
                try:
                    cli(['stop', '-s', SESSION], 'watchdog_stop.log', timeout=90)
                    break
                except Exception as error:
                    with (OUT / 'watchdog_stop.log').open('a') as stream:
                        stream.write(repr(error)+'\n')
            if (OUT / 'owned_endpoints.json').exists():
                orphan_endpoints(release=True)
            cli(['usage'], 'watchdog_usage.log', timeout=60)
            cli(['sessions'], 'watchdog_sessions.log', timeout=60)
            (OUT / 'watchdog_fired.json').write_text(json.dumps({'time': time.time(), 'session': SESSION}))
            return
        time.sleep(20)


def cell(code, name):
    path = OUT / f'cell_{name}.py'
    path.write_text(code, encoding='utf-8')
    cli(['exec', '-s', SESSION, '-f', str(path), '--timeout', '0'], name+'.log')


def stage(stage_name, command, summary):
    # sys.executable is deliberately resolved in the REMOTE kernel.
    cell('import subprocess, sys\n'
         f'result = subprocess.run([sys.executable, "-u", "/content/packet/remote.py", {command}], check=True)\n', stage_name)
    destination = OUT / summary
    cli(['download', '-s', SESSION, '/content/evidence/'+summary, str(destination)], 'downloads.log', timeout=180)
    record = json.loads(destination.read_text())
    if record.get('status') != 'PASS':
        raise RuntimeError(f'{stage_name}: required summary is not PASS')
    return record


def retrieve():
    cell('import pathlib, tarfile, hashlib, json\n'
         'root=pathlib.Path("/content/evidence")\n'
         'hashes={}\n'
         'for path in root.rglob("*"):\n'
         '    if path.is_file():\n'
         '        with path.open("rb") as stream: hashes[str(path.relative_to(root))]=hashlib.file_digest(stream,"sha256").hexdigest()\n'
         '(root/"hashes.json").write_text(json.dumps(hashes,indent=2))\n'
         'with tarfile.open("/content/evidence.tar","w") as archive: archive.add(root,arcname="evidence")\n', 'package')
    cli(['download', '-s', SESSION, '/content/evidence.tar', str(OUT / 'evidence.tar')], 'retrieval.log', timeout=600)
    with tarfile.open(OUT / 'evidence.tar') as archive:
        archive.extractall(OUT, filter='data')
    hashes = json.loads((OUT / 'evidence/hashes.json').read_text())
    for name, expected in hashes.items():
        with (OUT / 'evidence' / name).open('rb') as stream:
            actual = hashlib.file_digest(stream, 'sha256').hexdigest()
        if actual != expected:
            raise RuntimeError(f'Retrieval hash mismatch: {name}')
    (OUT / 'retrieval_verified.json').write_text(json.dumps({'files': len(hashes), 'status': 'PASS', 'time': time.time()}))


def run():
    now = time.time()
    previous = json.loads(STATE.read_text()) if STATE.exists() else {}
    run_id = time.strftime('rtdetr-20261123-sol-%Y%m%dT%H%M%SZ', time.gmtime(now))
    state = {'run_id': run_id, 'session': SESSION, 'operator': 'GPT Sol (sole designated operator)',
             'controller_pid': os.getpid(), 'allocation_request_unix': now,
             'hard_deadline_unix': min(previous.get('hard_deadline_unix', float('inf')), now + 25/3*3600 - 180),
             'stage_cap_CU': 25, 'rate_cap_CU_per_hour': 3, 'max_allocated_hours': 12,
             'account_balance_before_CU': 176.52, 'historical_project_spend_CU': 60.9,
             'guard_basis': 'Worst-case 3 CU/h; 3-minute stop margin; includes allocation setup/idle/retrieval',
             'status': 'GUARD_STARTING', 'teardown_verified': False}
    (OUT / 'owned_endpoints.json').write_text('[]')
    write_state(state)
    process = subprocess.Popen([sys.executable, str(HERE / 'control.py'), 'guard'],
                               creationflags=subprocess.CREATE_NO_WINDOW)
    state['guard_pid'] = process.pid
    state['status'] = 'ALLOCATING'
    write_state(state)
    print(json.dumps(state), flush=True)
    allocated = False
    try:
        cli(['new', '-s', SESSION, '--gpu', 'L4'], 'allocation.log', timeout=600)
        allocated = True
        cli(['usage'], 'usage_after_allocation.log', timeout=60)
        text = (OUT / 'usage_after_allocation.log').read_text()
        import re
        rate = float(re.search(r'Usage rate:\s*([\d.]+)', text).group(1))
        assignments = int(re.search(r'Active assignments:\s*(\d+)', text).group(1))
        if not 0 < rate <= 3 or assignments != 1:
            raise RuntimeError(f'Admission failed: rate {rate}, assignments {assignments}')
        state.update({'status': 'SETUP', 'live_rate_CU_per_hour': rate})
        write_state(state)
        cli(['upload', '-s', SESSION, str(OUT / 'packet.tar.gz'), '/content/packet.tar.gz'], 'upload.log', timeout=240)
        cell('import tarfile\nwith tarfile.open("/content/packet.tar.gz") as archive: archive.extractall("/content/packet",filter="data")\n', 'unpack')
        stage('setup', '"setup"', 'setup.json')
        state['status'] = 'PILOT'; write_state(state)
        pilot = stage('pilot', '"train", "--arm", "pilot", "--epochs", "1"', 'pilot_summary.json')
        if pilot['successful_updates'] < 0.95*pilot['attempted_updates']:
            raise RuntimeError('Pilot successful-update fraction below predeclared 95%')
        # No model score used. Reserve 45 min inference/retrieval + 15 min safety;
        # use 1.25x measured full-epoch wall time; minimum meaningful baseline 10.
        usable = state['hard_deadline_unix']-time.time()-3600
        epoch_s = pilot['seconds']*1.25
        baseline_epochs = min(50, int(usable//epoch_s))
        if baseline_epochs < 10:
            raise RuntimeError('Pilot projects fewer than 10 baseline epochs within cap')
        remaining = usable - baseline_epochs*epoch_s
        adapt_epochs = 10 if baseline_epochs == 50 and remaining >= 10*epoch_s*8000/10635 else 0
        plan = {'run_id': run_id, 'baseline_epochs': baseline_epochs, 'adaptation_epochs': adapt_epochs,
                'pilot_seconds': pilot['seconds'], 'conservative_epoch_seconds': epoch_s,
                'basis': 'Throughput and remaining budget only; no selection/test scores',
                'status': 'WAITING_FOR_COMMITTED_PLAN', 'created_unix': time.time()}
        (OUT / 'proposed_plan.json').write_text(json.dumps(plan, indent=2))
        state['status'] = 'WAITING_FOR_COMMITTED_PLAN'; write_state(state)
        print(json.dumps(plan), flush=True)
        # A lost LLM turn cannot idle away the allocation: ten-minute plan window.
        until = time.time()+600
        while not (OUT / 'approved_plan.json').exists():
            if time.time() >= until:
                raise TimeoutError('No committed throughput amendment within 10 minutes')
            time.sleep(10)
        approved = json.loads((OUT / 'approved_plan.json').read_text())
        assert approved['baseline_epochs'] == baseline_epochs and approved['adaptation_epochs'] == adapt_epochs
        state['status'] = 'BASELINE'; write_state(state)
        baseline = stage('baseline', f'"train", "--arm", "baseline", "--epochs", "{baseline_epochs}"', 'baseline_summary.json')
        if baseline['successful_updates'] < 0.95*baseline['attempted_updates']:
            raise RuntimeError('Baseline successful-update fraction below predeclared 95%; no adaptation')
        if adapt_epochs:
            state['status'] = 'ADAPTATION'; write_state(state)
            stage('adaptation', f'"train", "--arm", "adaptation", "--epochs", "{adapt_epochs}"', 'adaptation_summary.json')
        for arm in ['baseline'] + (['adaptation'] if adapt_epochs else []):
            state['status'] = 'INFERENCE_'+arm.upper(); write_state(state)
            stage('infer_'+arm, f'"infer", "--arm", "{arm}"', arm+'_inference.json')
        state['status'] = 'RETRIEVING'; write_state(state)
        retrieve()
        state['status'] = 'COMPLETE'
    except BaseException as error:
        state['status'] = 'FAILED'
        state['error'] = repr(error)
        write_state(state)
        if allocated:
            try:
                retrieve()
            except Exception as retrieval_error:
                state['retrieval_error'] = repr(retrieval_error)
        print(json.dumps(state), flush=True)
    finally:
        # Also stop if `new` timed out after creating a server assignment.
        try:
            cli(['stop', '-s', SESSION], 'stop.log', timeout=120)
            if (OUT / 'owned_endpoints.json').exists():
                # Avoid re-unassigning an endpoint already released by `stop`.
                owned = set(json.loads((OUT / 'owned_endpoints.json').read_text()))
                current = set(orphan_endpoints())
                (OUT / 'owned_endpoints.json').write_text(json.dumps(sorted(owned & current)))
                if owned & current:
                    orphan_endpoints(release=True)
            cli(['usage'], 'usage_final.log', timeout=60)
            cli(['sessions'], 'sessions_final.log', timeout=60)
            usage = (OUT / 'usage_final.log').read_text()
            sessions = (OUT / 'sessions_final.log').read_text()
            state['teardown_verified'] = 'Active assignments: 0' in usage and 'No active sessions found' in sessions
        except Exception as error:
            state['stop_error'] = repr(error)
        state['completed_unix'] = time.time()
        state['allocated_hours_upper_bound'] = (time.time()-now)/3600
        state['CU_upper_bound_at_admitted_rate'] = state['allocated_hours_upper_bound']*state.get('live_rate_CU_per_hour',3)
        write_state(state)
        print(json.dumps(state), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['run', 'guard'])
    args = parser.parse_args()
    guard() if args.mode == 'guard' else run()
