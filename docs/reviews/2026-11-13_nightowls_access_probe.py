import importlib.util, json, os, subprocess, sys, time
W = sys.argv[1]; OUT = sys.argv[2]; FIX = sys.argv[3]
spec = importlib.util.spec_from_file_location('pilot', W); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
assert m.EXECUTION_AUTHORIZED is False
cmd = m.worker_command(FIX)
r = {'base': cmd[0], 'flags': cmd[1:3], 'controller_pid': os.getpid(), 'controller_exe': sys.executable}
t0 = time.monotonic()
p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL, text=True)
line = json.loads(p.stdout.readline())
r.update(popen_pid=p.pid, child=line, pid_equal=line['pid'] == p.pid, parent_equal=line['parent_pid'] == os.getpid())
try:
    p.wait(timeout=2); r['timeout_raised'] = False
except subprocess.TimeoutExpired:
    r['timeout_raised'] = True; p.kill(); p.wait()
r.update(returncode=p.returncode, reaped=p.poll() is not None, seconds=round(time.monotonic() - t0, 3))
# Negative: the same command started through an intermediate interpreter must fail the parent assertion before runpy.
neg = subprocess.run([sys.executable, '-I', '-c', 'import subprocess,sys,json; c=json.loads(sys.argv[1]); sys.exit(subprocess.run(c, capture_output=True, text=True, timeout=10).stderr.strip().splitlines()[-1] == "AssertionError: unexpected_worker_parent" and 7 or 3)', json.dumps(cmd)], timeout=20)
r['intermediate_parent_rejected'] = neg.returncode == 7
r['network_requests'] = 0
json.dump(r, open(OUT, 'w'), indent=2); print(json.dumps(r, indent=2))
