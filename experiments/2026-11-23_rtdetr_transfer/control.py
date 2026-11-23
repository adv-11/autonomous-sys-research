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
SESSION = 'rtdetr1123-sol3'
CLI = str(Path.home() / '.local/bin/colab.exe')
CLI_PYTHON = str(Path.home() / 'AppData/Roaming/uv/tools/google-colab-cli/Scripts/python.exe')


def owned_assignment(mode):
    result = subprocess.run([CLI_PYTHON, str(HERE / 'allocation.py'), mode],
                            capture_output=True, text=True, timeout=120, check=True,
                            env={**os.environ, 'COLAB_CLI_ASSIGN_RETRIES': '0',
                                 'COLAB_CLI_REQUEST_TIMEOUT': '90'})
    record = json.loads(result.stdout)
    with (OUT / 'ownership_actions.jsonl').open('a') as stream:
        stream.write(json.dumps({'unix': time.time(), 'mode': mode, **record})+'\n')
    return record


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
    """Independently release ONLY the persisted notebook UUID at deadline."""
    while True:
        state = json.loads(STATE.read_text())
        if state.get('teardown_verified'):
            return
        if time.time() >= state['hard_deadline_unix']:
            result = owned_assignment('release')
            verified = not owned_assignment('resolve').get('assigned', True)
            (OUT / 'watchdog_fired.json').write_text(json.dumps(
                {'time': time.time(), 'session': SESSION, 'result': result,
                 'own_assignment_gone': verified}))
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
    contract = json.loads((HERE / 'config.json').read_text())
    if not contract['execution_permitted']:
        raise RuntimeError('Compute is blocked by the saved contract; await explicit availability instruction')
    cli(['usage'], 'parallel_admission_usage.log', timeout=60)
    cli(['sessions'], 'parallel_admission_sessions.log', timeout=60)
    import re, uuid
    admission = (OUT / 'parallel_admission_usage.log').read_text()
    base_rate = float(re.findall(r'Usage rate:\s*([\d.]+)', admission)[-1])
    listing = (OUT / 'parallel_admission_sessions.log').read_text().splitlines()
    protected = 'gpu-t4-s-usw4b1-15opi0xtfafn2'
    unexpected = [line for line in listing if 'Hardware:' in line and protected not in line]
    if unexpected:
        raise RuntimeError('An additional unowned assignment exists; no research allocation requested')
    now = time.time()
    previous = json.loads(STATE.read_text()) if STATE.exists() else {}
    (OUT / 'prior_live_state.json').write_text(json.dumps(previous, indent=2))
    request = {'session': SESSION, 'notebook_uuid': str(uuid.uuid4()), 'protected_user_endpoint': protected}
    (OUT / 'allocation_request.json').write_text(json.dumps(request, indent=2))
    run_id = time.strftime('rtdetr-20261123-sol-%Y%m%dT%H%M%SZ', time.gmtime(now))
    state = {'run_id': run_id, 'session': SESSION, 'operator': 'GPT Sol (sole designated operator)',
             'controller_pid': os.getpid(), 'allocation_request_unix': now,
             'hard_deadline_unix': now + min(24.99/3, 11.888)*3600 - 300,
             'stage_cap_CU': 25, 'rate_cap_CU_per_hour': 3, 'max_allocated_hours': 12,
             'account_balance_context_CU': 176.41, 'preexisting_user_rate_CU_per_hour': base_rate, 'notebook_uuid': request['notebook_uuid'], 'historical_project_spend_CU': 60.9,
             'guard_basis': 'Remaining24.99CU/11.888h, conservative3CU/h, 5-minute stop margin; exact own UUID only; user costs excluded',
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
        ownership = owned_assignment('allocate')
        state['endpoint'] = ownership['endpoint']
        write_state(state)
        print(json.dumps(ownership), flush=True)
        allocated = True
        cli(['usage'], 'usage_after_allocation.log', timeout=60)
        text = (OUT / 'usage_after_allocation.log').read_text()
        import re
        total_rate = float(re.findall(r'Usage rate:\s*([\d.]+)', text)[-1])
        cli(['sessions'], 'parallel_after_sessions.log', timeout=60)
        user_present = protected in (OUT / 'parallel_after_sessions.log').read_text()
        rate = total_rate - (base_rate if user_present else 0)
        if not 0 < rate <= 3:
            raise RuntimeError(f'Owned rate admission failed: {rate}; total {total_rate}, preexisting {base_rate}')
        state['rate_basis'] = {'total_after': total_rate, 'preexisting_user_rate': base_rate,
                               'protected_user_assignment_still_present': user_present,
                               'account_balance_delta_used_for_billing': False}
        state.update({'status': 'SETUP', 'live_rate_CU_per_hour': rate})
        write_state(state)
        cell('import subprocess, pathlib\n'
             'gpu=subprocess.check_output(["nvidia-smi","--query-gpu=name,memory.total","--format=csv,noheader"],text=True)\n'
             'print(gpu)\nassert "L4" in gpu, "Requested L4 did not become available"\n'
             'pathlib.Path("/content/evidence").mkdir(exist_ok=True)\n'
             'pathlib.Path("/content/evidence/hardware.txt").write_text(gpu)\n', 'hardware')
        cli(['download', '-s', SESSION, '/content/evidence/hardware.txt', str(OUT / 'hardware.txt')], 'hardware_download.log', timeout=60)
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
        try:
            if allocated:
                cli(['stop', '-s', SESSION], 'stop.log', timeout=90)
            owned_assignment('release')
            state['teardown_verified'] = not owned_assignment('resolve').get('assigned', True)
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
