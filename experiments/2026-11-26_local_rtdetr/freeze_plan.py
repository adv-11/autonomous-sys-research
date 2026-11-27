"""GPT Sol: select epochs using measured throughput only, before scientific fit."""
import json
import math
import subprocess
import time
from local import HERE, OUT, load, sha


def main():
    assert not (OUT/'baseline').exists(),'Baseline already started; no retrospective plan'
    assert not list(OUT.glob('*_pedestrian.npz')),'Held-out predictions already exist'
    pilot=load(OUT/'pilot_summary.json')
    batch=pilot['batch']
    # Epoch timing includes the native loader/loss/backward/EMA path. The pilot
    # summary also includes its checkpoint serialization overhead.
    seconds_per_image=pilot['seconds']/pilot['images']
    deadline=load(OUT/'deadline.json')['deadline_unix']
    remaining=deadline-time.time()
    continuation_seconds=seconds_per_image*8000*5*2*1.25
    estimates={str(n):seconds_per_image*10635*n*1.25+continuation_seconds+7200
               for n in (50,30,20,12)}
    epochs=next((n for n in (50,30,20,12) if estimates[str(n)]<=remaining),None)
    plan=dict(researcher='GPT Sol',frozen_unix=time.time(),pilot_sha256=sha(OUT/'pilot_summary.json'),
        pilot_images=pilot['images'],pilot_seconds=pilot['seconds'],seconds_per_image=seconds_per_image,
        batch=batch,baseline_epochs=epochs,continuation_epochs=5,continuation_images=8000,
        continuation_attempted_updates=5*math.ceil(8000/batch),
        safety_factor=1.25,inference_evaluation_reserve_seconds=7200,remaining_seconds=remaining,
        projected_all_stages_seconds=estimates,status='FROZEN' if epochs else 'DOES_NOT_FIT',
        pilot_weights_discarded=True,day_control_manifest_sha256=sha(OUT/'manifest_day_control.json'),
        mixed_manifest_sha256=sha(__import__('local').PIN/'manifest_adaptation.json'),
        baseline_augmentation_stop_epoch=epochs-3 if epochs else None,
        continuation_augmentation_stop_epoch=2,
        initialization='Official init for baseline; same final baseline EMA for both continuations; fresh AdamW/EMA seed0',
        selection='Final declared EMA; no held-out checkpoint/policy changes',
        deadline_unix=deadline)
    (HERE/'plan.json').write_text(json.dumps(plan,indent=2))
    print(json.dumps(plan,indent=2))


if __name__=='__main__':
    main()
