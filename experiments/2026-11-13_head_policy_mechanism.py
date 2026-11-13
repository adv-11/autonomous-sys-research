"""GPT Sol: frozen learned-head x native-policy bundles and expanded native panel.

No training. Private image IDs, batches, manifest and raw debug stay in outputs/.
The two native cells are replay controls, not a claim that NMS alone is isolated.
"""
from __future__ import annotations
import argparse
import collections
import hashlib
import importlib.util
import inspect
import json
import math
from pathlib import Path
import shutil
import sys
import tarfile
import time

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('pilot', Path(__file__).with_name('2026-11-10_transfer_pilot.py'))
pilot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pilot)
read, write, sha = pilot.read, pilot.write, pilot.sha
PRIVATE = Path('C:/Users/Advait/autonomous-sys-research')
OLD = PRIVATE/'outputs/colab/dual_head_20261111'
H4_SHA = 'cd966fb75c2fd5bbbe65e2aa9f10d7071f5af5b481d8f60a9ba8a601711ca5ea'
WEIGHT_SHA = '646f8bc3fe0a656803d95c294f7852321748cb29d13466a1af8862e2db384a1b'


def prepare(root):
    from threshold_transfer.acdc import AGGREGATE_FILES, convert_acdc, parse_file_name
    root = Path(root); packet = root/'packet'; packet.mkdir(parents=True, exist_ok=True)
    assert sha(OLD/'packet/manifest.json') == H4_SHA
    old = read(OLD/'packet/manifest.json')
    shutil.copyfile(OLD/'packet/manifest.json', packet/'manifest_A.json')
    acdc = PRIVATE/'data/acdc/extracted'
    adverse_path, normal_path = (acdc/AGGREGATE_FILES[('train', r)] for r in (False, True))
    adverse, normal = read(adverse_path), read(normal_path)
    assert len(adverse['images']) == 1600 and len(normal['images']) == 800
    panels = {k: old['panels'][k] for k in ('source_selection','coco_reference')}
    for condition in ('fog','night','rain','snow'):
        ims = [i for i in adverse['images'] if parse_file_name(i['file_name'])['condition']==condition]
        refs = [i for i in normal['images'] if parse_file_name(i['file_name'])['condition']==condition]
        keys = {parse_file_name(i['file_name'])['pair_key'] for i in refs}
        paired = [i for i in ims if parse_file_name(i['file_name'])['pair_key'] in keys]
        for name, doc, images, ref in ((condition,adverse,ims,False),
                (condition+'_paired',adverse,paired,False),(condition+'_normal',normal,refs,True)):
            panel = convert_acdc(pilot.native_subset(doc,images),split='train',reference=ref,
                ignore_policy='acdc_iscrowd_v1_provisional',check_masks=False)
            panel['annotations']=[a for a in panel['annotations'] if a['category'] in ('person','rider')]
            for a in panel['annotations']:
                a.setdefault('attributes',{})['pilot_native_category']=a['category']; a['category']='human'
            for i in panel['images']: i['file_name']='images/acdc/'+i['file_name']
            panels[name]=panel
    write(packet/'manifest_B.json',dict(researcher='GPT Sol',selection='ALL official train1600 and annotated train800 refs; no GT selection',
        source_files=[dict(path=str(p),sha256=sha(p)) for p in (adverse_path,normal_path)],panels=panels))
    config = dict(researcher='GPT Sol',base='1a8c783',prespecified_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
        manifest_A_sha256=H4_SHA,manifest_B_sha256=sha(packet/'manifest_B.json'),
        implementation='ultralytics==8.4.197',weight_sha256=WEIGHT_SHA,imgsz=1280,batch=8,
        half=False,rect=False,floor=.0001,cap=3000,max_nms=30000,nms_iou=.7,classes=[0],agnostic_nms=False,
        objective=.9,threshold_rule='highest observed source score; inclusive whole ties; infeasible/undefined retained',
        original_thresholds={h:read(REPO/'docs/gpt/2026-11-11_sol_dual_head_transfer.json')['heads'][f'yolo26s_{h}']['source_selection']['threshold'] for h in ('o2o','o2m')},
        cells=['o2o_K','o2o_N','o2m_K','o2m_N'],
        K='native all-class anchor topk, all-class flattened topk3000, person/floor filter, no NMS',
        N='native max-class, floor/person filter, max_nms30000, class-aware NMS .70, cap3000',
        contrast_orientation=dict(head='o2o minus o2m within each bundle',policy='K minus N within each head',
            interaction='(o2o_K-o2m_K)-(o2o_N-o2m_N)',condition='night contrast minus COCO-reference contrast'),
        direct_and_boundary='D=K(t_h)-N(t_h); B=cell(t_cell*)-cell(t_h); retain exact TP/FP additive identity',
        reporting='all conditions, recall/FPPI, direct original head thresholds and per-cell .90 reselection, ceiling and operating shared/unique GT',
        native_tolerance=dict(counts_classes='exact',box_atol_pixels=.002,score_atol=1e-6,metric_counts='exact',original_H4_metric_counts='exact'),
        budget=dict(max_CU=20,max_allocated_hours=6,max_admission_CU_hr=6,prior_batch_allocated_seconds=0),
        interpretation='policy-bundle intervention, no causal darkness/NMS-only/novelty; train/val recordings overlap; G0 pending')
    write(packet/'config.json',config); write(REPO/'configs/research/head_policy_mechanism_20261113.json',config)
    # Images are transferred once; source/ref512 and Stage A are reused by Stage B.
    images = {i['file_name']:i for m in (old,read(packet/'manifest_B.json')) for p in m['panels'].values() for i in p['images']}
    weight=Path('C:/Users/Advait/ar-work/weights/yolo26s.pt'); assert sha(weight)==WEIGHT_SHA
    with tarfile.open(root/'packet.tar','w') as tar:
        for name in ('manifest_A.json','manifest_B.json','config.json'): tar.add(packet/name,arcname='packet/'+name)
        for name in ('2026-11-10_transfer_pilot.py',Path(__file__).name): tar.add(Path(__file__).with_name(name),arcname='packet/experiments/'+name)
        for path in (REPO/'src/threshold_transfer').glob('*.py'): tar.add(path,arcname='packet/src/threshold_transfer/'+path.name)
        tar.add(weight,arcname='packet/yolo26s.pt')
        for name in sorted(images,key=lambda n:(('/train/' in n or '/train_ref/' in n),n)):
            native=(Path('C:/Users/Advait/det-eval-2d/datasets/coco/val2017')/name.removeprefix('images/coco/')) if name.startswith('images/coco/') else acdc/'rgb_anon_trainvaltest/rgb_anon'/name.removeprefix('images/acdc/')
            assert native.is_file(),native
            tar.add(native,arcname='packet/'+name)
    chunks=root/'chunks'; chunks.mkdir(exist_ok=True)
    with (root/'packet.tar').open('rb') as f:
        n=0
        while data:=f.read(4*1024**2): (chunks/f'part{n:04d}').write_bytes(data); n+=1
    record=dict(bytes=(root/'packet.tar').stat().st_size,sha256=sha(root/'packet.tar'),chunks=n,unique_images=len(images),
        manifests={s:sha(packet/f'manifest_{s}.json') for s in ('A','B')},config_sha256=sha(packet/'config.json'),
        script_sha256=sha(__file__),pilot_sha256=sha(pilot.__file__),
        estimated_transfer_minutes=(root/'packet.tar').stat().st_size/964546560*22,
        estimated_inference_minutes=25,estimated_rate_CU_hr=1.94,
        panels={s:{k:len(v['images']) for k,v in read(packet/f'manifest_{s}.json')['panels'].items()} for s in ('A','B')})
    write(root/'packet_record.json',record); print(json.dumps(record),flush=True)


def infer(root,limit_images=None,correction=False):
    import cv2
    import logging
    import numpy as np
    import torch
    import ultralytics
    from ultralytics import YOLO
    from ultralytics.models.yolo.detect.predict import DetectionPredictor
    from ultralytics.utils import ops, nms, LOGGER
    from ultralytics.nn.modules.head import Detect
    from ultralytics.data.augment import LetterBox
    root=Path(root); result=root/'results'/('correction_last_native_batch' if correction else '')
    result.mkdir(parents=True,exist_ok=True)
    cfg=read(root/'config.json'); assert ultralytics.__version__=='8.4.197'
    assert sha(root/'yolo26s.pt')==WEIGHT_SHA
    manifests={s:read(root/f'manifest_{s}.json') for s in ('A','B')}
    images={i['image_id']:i for m in manifests.values() for p in m['panels'].values() for i in p['images']}
    a_ids={i['image_id'] for p in manifests['A']['panels'].values() for i in p['images']}
    images=sorted(images.values(),key=lambda i:(i['image_id'] not in a_ids,i['file_name']))
    if limit_images is not None: images=images[:limit_images]
    if correction:
        request=read(root/'native_batch_correction.json')
        by_id={i['image_id']:i for i in images}
        images=[by_id[i] for i in request['original_H4_final_batch_ids']]
        assert len(images)==5
        write(result/'prespecified_correction.json',request)
    for name,obj in (('Detect',Detect),('NMS',nms),('ops',ops),('DetectionPredictor',DetectionPredictor),('LetterBox',LetterBox)):
        (result/(name+'_source.py')).write_text(inspect.getsource(obj),encoding='utf-8')
    warnings=[]
    class Censor(logging.Handler):
        def emit(self, rec):
            msg=rec.getMessage()
            if 'time limit' in msg.lower() or 'nan' in msg.lower(): warnings.append(msg)
    LOGGER.addHandler(Censor())
    def tensor_hash(t): return hashlib.sha256(t.detach().contiguous().cpu().numpy().tobytes()).hexdigest()
    # Native forward branches are separately loaded/fused by official AutoBackend.
    for h in ('o2o','o2m'):
        status=dict(status='RUNNING',head=h,torch=torch.__version__,ultralytics=ultralytics.__version__,
            python=sys.version,numpy=np.__version__,opencv=cv2.__version__,cuda=torch.version.cuda,
            cudnn=torch.backends.cudnn.version(),deterministic_algorithms=torch.are_deterministic_algorithms_enabled(),
            device=torch.cuda.get_device_name(0),device_memory_bytes=torch.cuda.get_device_properties(0).total_memory,
            batches=[],started=time.time(),config_sha256=sha(root/'config.json'),checkpoint_sha256=sha(root/'yolo26s.pt'))
        status_path=result/f'{h}_status.json'; write(status_path,status)
        model=YOLO(str(root/'yolo26s.pt'))
        initial=model.model.model[-1]
        status['branches_before']={k:getattr(initial,k,None) is not None for k in ('cv2','cv3','one2one_cv2','one2one_cv3')}
        assert all(status['branches_before'].values())
        class CapturePredictor(DetectionPredictor):
            def setup_model(self,*args,**kwargs):
                super().setup_model(*args,**kwargs)
                self.branch_calls={'o2o':0,'o2m':0}
                active=self.model.model.model[-1]
                def counter(key):
                    def hook(*unused): self.branch_calls[key]+=1
                    return hook
                for key,attr in (('o2o','one2one_cv2'),('o2m','cv2')):
                    for module in getattr(active,attr,None) or []: module.register_forward_hook(counter(key))

            def postprocess(self,preds,img,orig_imgs,**kwargs):
                active=self.model.model.model[-1]
                raw=preds[1]
                raw=raw['one2one' if h=='o2o' else 'one2many'] if 'one2one' in raw else raw
                decoded=active._inference(raw)
                native_format='xyxy' if active.end2end or active.xyxy else 'xywh'
                assert native_format==('xyxy' if h=='o2o' else 'xywh')
                evidence=dict(input_shape=list(img.shape),input_sha256=tensor_hash(img),
                    raw_box_sha256=tensor_hash(raw['boxes']),raw_scores_sha256=tensor_hash(raw['scores']),
                    decoded_sha256=tensor_hash(decoded),decoded_shape=list(decoded.shape),format=native_format,
                    branch_calls=self.branch_calls.copy(),
                    backend_end2end=self.model.end2end,head_end2end=active.end2end,head_max_det=active.max_det,
                    branches_after={k:getattr(active,k,None) is not None for k in ('cv2','cv3','one2one_cv2','one2one_cv3')},
                    raw_person_above_floor=(decoded[:,4,:]>cfg['floor']).sum(1).cpu().tolist(),
                    argmax_person_above_floor=((decoded[:,4:,:].argmax(1)==0)&(decoded[:,4:,:].amax(1)>cfg['floor'])).sum(1).cpu().tolist(),
                    original_shapes=[list(x.shape[:2]) for x in orig_imgs])
                evidence['resolved_args']={k:getattr(self.args,k,None) for k in ('task','mode','batch','imgsz','device','rect','conf','iou','max_det','nms','classes','agnostic_nms','augment','half','compile')}
                evidence['selector_limits']=dict(K_all_class_topk=3000,N_max_nms=30000,N_final_max_det=3000,
                    N_time_limit_seconds=2.0+.05*len(orig_imgs),N_implementation='torchvision' if 'torchvision' in sys.modules else 'TorchNMS')
                evidence['letterbox']=[]
                for orig in orig_imgs:
                    oh,ow=orig.shape[:2]; ih,iw=img.shape[2:]
                    gain=min(ih/oh,iw/ow); resized=[round(ow*gain),round(oh*gain)]
                    dw,dh=(iw-resized[0])/2,(ih-resized[1])/2
                    evidence['letterbox'].append(dict(original_hw=[oh,ow],input_hw=[ih,iw],gain=gain,
                        resized_wh=resized,pad_ltrb=[round(dw-.1),round(dh-.1),round(dw+.1),round(dh+.1)],
                        scale_boxes_ratio_pad='official inferred from input and original shapes; no manual inverse'))
                outputs={}
                policies=('K','N') if any(i['image_id'] in a_ids for i in current_batch) else (('K',) if h=='o2o' else ('N',))
                for policy in policies:
                    d=decoded.clone()
                    if policy=='K':
                        if native_format=='xywh': d[:,:4,:]=ops.xywh2xyxy(d[:,:4,:].transpose(1,2)).transpose(1,2)
                        saved_max_det=active.max_det
                        active.max_det=3000
                        try: selected=active.postprocess(d.permute(0,2,1).clone())
                        finally: active.max_det=saved_max_det
                        outputs[policy]=nms.non_max_suppression(selected.clone(),cfg['floor'],.7,[0],False,max_det=3000,end2end=True)
                    else:
                        if native_format=='xyxy': d[:,:4,:]=ops.xyxy2xywh(d[:,:4,:].transpose(1,2)).transpose(1,2)
                        outputs[policy]=nms.non_max_suppression(d.clone(),cfg['floor'],.7,[0],False,max_det=3000,end2end=False)
                    evidence[policy+'_selected_count']=[len(x) for x in outputs[policy]]
                    for pred,orig in zip(outputs[policy],orig_imgs): pred[:,:4]=ops.scale_boxes(img.shape[2:],pred[:,:4],orig.shape)
                native=super().postprocess(preds,img,orig_imgs,**kwargs)
                self.captured=outputs
                self.stage_evidence=evidence
                self.native_checks=[]
                for native_out,replay in zip(native,outputs['K' if h=='o2o' else 'N']):
                    ref=native_out.boxes.data
                    same_shape=ref.shape==replay.shape
                    self.native_checks.append(dict(shape_equal=same_shape,
                        classes_equal=same_shape and torch.equal(ref[:,5],replay[:,5]),
                        max_box_error=float((ref[:,:4]-replay[:,:4]).abs().max()) if same_shape and ref.numel() else (0 if same_shape else None),
                        max_score_error=float((ref[:,4]-replay[:,4]).abs().max()) if same_shape and ref.numel() else (0 if same_shape else None)))
                if not list(result.glob(h+'_debug_*.pt')):
                    torch.save(dict(input=img[:1].cpu(),raw_boxes=raw['boxes'][:1].cpu(),raw_scores=raw['scores'][:1].cpu(),
                        decoded=decoded[:1].cpu(),metadata=evidence),result/f'{h}_debug_first_image.pt')
                return native
        torch.cuda.reset_peak_memory_stats()
        completed=set()
        for prior_path in sorted(result.glob(f'{h}_batch_*.json')):
            prior=read(prior_path)
            if prior.get('validated'):
                assert not completed.intersection(prior['image_ids']),'duplicate completed IDs'
                completed.update(prior['image_ids'])
        assert completed<={i['image_id'] for i in images}
        pending=[i for i in images if i['image_id'] not in completed]
        for offset in range(0,len(pending),cfg['batch']):
            start=len(completed)+offset
            current_batch=pending[offset:offset+cfg['batch']]
            path=result/f'{h}_batch_{start:04d}.json'
            if path.exists():
                assert not read(path).get('validated'),'completed batch collision'
                path.rename(path.with_suffix('.failed.json'))
            t=time.monotonic()
            native=list(model.predict([str(root/i['file_name']) for i in current_batch],predictor=CapturePredictor,
                conf=cfg['floor'],max_det=3000,imgsz=1280,device=0,half=False,rect=False,batch=8,
                classes=[0],iou=.7,agnostic_nms=False,augment=False,verbose=False,save=False,stream=True,nms=h=='o2m'))
            predictor=model.predictor
            cells={p:[x.detach().cpu().tolist() for x in rows] for p,rows in predictor.captured.items()}
            batch=dict(image_ids=[i['image_id'] for i in current_batch],cells=cells,
                native=[o.boxes.data.cpu().tolist() for o in native],stage=predictor.stage_evidence,
                native_checks=predictor.native_checks,seconds=time.monotonic()-t,validated=False)
            # Raw final-cell and control evidence is committed before any validity decision.
            path.write_text(json.dumps(batch,indent=2,allow_nan=True),encoding='utf-8')
            assert not warnings,warnings
            assert batch['stage']['branch_calls'][h]>0 and batch['stage']['branch_calls']['o2m' if h=='o2o' else 'o2o']==0
            assert len(native)==len(current_batch)
            for out,image in zip(native,current_batch): assert tuple(out.orig_shape)==(image['height'],image['width'])
            batch['native_replay_pass']=all(check['shape_equal'] and check['classes_equal'] and
                check['max_box_error']<=.002 and check['max_score_error']<=1e-6 for check in batch['native_checks'])
            # A failed replay restricts the swap interpretation, not native replication.
            status['native_replay_pass']=status.get('native_replay_pass',True) and batch['native_replay_pass']
            for rows in cells.values():
                for preds_image in rows:
                    for x1,y1,x2,y2,score,cls in preds_image:
                        assert cls==0 and x2>=x1 and y2>=y1 and all(math.isfinite(v) for v in (x1,y1,x2,y2,score)) and 0<=score<=1
            batch['validated']=True; write(path,batch)
            status['batches'].append(dict(start=start,images=len(current_batch),seconds=batch['seconds']))
            status.update(completed_images=start+len(current_batch),
                peak_allocated_bytes=torch.cuda.max_memory_allocated(),
                peak_reserved_bytes=torch.cuda.max_memory_reserved()); write(status_path,status)
            write(result/'checkpoint.json',dict(head=h,completed_images=start+len(current_batch),expected_images=len(images),last_batch=str(path)))
            if start%128==0: print(json.dumps(dict(head=h,completed=start+len(current_batch),total=len(images))),flush=True)
        status.update(status='COMPLETE',ended=time.time()); write(status_path,status)
        del model
        torch.cuda.empty_cache()
    write(result/'inference_complete.json',dict(status='COMPLETE',unique_images=len(images),A_unique=len(a_ids),heads=2))


def prepare_recovery(root):
    """One bounded serial recovery: restore completed A, transfer only train RGB."""
    root=Path(root); prior=PRIVATE/'outputs/colab/head_policy_20261113'
    operation=read(prior/'operation.json')
    assert operation['owned_teardown_verified'] and operation['status']=='ERROR'
    assert read(prior/'stage_A/results/stage_A_process_status.json')['returncode']==0
    packet=root/'packet';packet.mkdir(parents=True,exist_ok=True)
    for name in ('manifest_A.json','manifest_B.json','config.json'): shutil.copyfile(prior/'packet'/name,packet/name)
    retained=prior/'evidence_final.tar.gz';assert sha(retained)==operation['evidence_sha256']
    for name in ('stage_A_first_pass_aggregate.json','stage_A_aggregate.json','native_batch_correction.json',
            'correction_vs_original.json','historical_native_discrepancy.json','historical_output_controls.json',
            'actual_peer_exchange.json','stage_B_prefix_attempt.json','correction_evidence.tar.gz','operator_milestones.jsonl'):
        shutil.copyfile(prior/name,root/name)
    write(root/'previous_operation.json',operation)
    previous=[read(p) for p in root.parent.glob('head_policy_20261113*/operation.json')]
    assert all(p.get('owned_teardown_verified') for p in previous)
    write(root/'previous_operations.json',previous)
    for phase in ('probe','stage_A'):
        dest=root/phase/'results';dest.mkdir(parents=True,exist_ok=True)
        for h in ('o2o','o2m'): shutil.copyfile(prior/phase/'results'/f'{h}_status.json',dest/f'{h}_status.json')
    a=read(packet/'manifest_A.json');b=read(packet/'manifest_B.json')
    a_ids={i['image_id'] for p in a['panels'].values() for i in p['images']}
    images={i['image_id']:i for p in b['panels'].values() for i in p['images'] if i['image_id'] not in a_ids}
    assert len(images)==2400
    acdc=PRIVATE/'data/acdc/extracted/rgb_anon_trainvaltest/rgb_anon'
    weight=Path('C:/Users/Advait/ar-work/weights/yolo26s.pt');assert sha(weight)==WEIGHT_SHA
    with tarfile.open(root/'packet.tar','w') as tar:
        for name in ('manifest_A.json','manifest_B.json','config.json'): tar.add(packet/name,arcname='packet/'+name)
        for name in ('2026-11-10_transfer_pilot.py',Path(__file__).name): tar.add(Path(__file__).with_name(name),arcname='packet/experiments/'+name)
        for path in (REPO/'src/threshold_transfer').glob('*.py'):tar.add(path,arcname='packet/src/threshold_transfer/'+path.name)
        tar.add(weight,arcname='packet/yolo26s.pt')
        tar.add(retained,arcname='packet/retained_stage_A.tar.gz')
        for image in sorted(images.values(),key=lambda i:i['file_name']):
            native=acdc/image['file_name'].removeprefix('images/acdc/');assert native.is_file()
            tar.add(native,arcname='packet/'+image['file_name'])
    chunks=root/'chunks';chunks.mkdir(exist_ok=True)
    with (root/'packet.tar').open('rb') as f:
        n=0
        while data:=f.read(4*1024**2):(chunks/f'part{n:04d}').write_bytes(data);n+=1
    record=dict(bytes=(root/'packet.tar').stat().st_size,sha256=sha(root/'packet.tar'),chunks=n,
        retained_stage_A_sha256=sha(retained),prior_operation_sha256=sha(prior/'operation.json'),
        unique_images=3333,transfer_images=2400,completed_image_heads_restored=1866,
        manifests={s:sha(packet/f'manifest_{s}.json') for s in ('A','B')},config_sha256=sha(packet/'config.json'),
        script_sha256=sha(__file__),pilot_sha256=sha(pilot.__file__),
        estimated_transfer_minutes=(root/'packet.tar').stat().st_size/490741760*11,
        estimated_inference_minutes=25,estimated_rate_CU_hr=1.94,
        recovery='one correction for ConnectionResetError10054 on original chunk1373; serial uploads; no repeat of completed A inference')
    write(root/'packet_record.json',record);print(json.dumps(record),flush=True)




def operate(root):
    """Host-only deadline, retrieval and finally-stop; survives agent/token exhaustion.

    One named ownership attempt; no automatic allocation/retry or unrelated stop.
    CLI completion is not remote-child success. All paths are private artifacts.
    """
    from datetime import datetime, timezone
    import os
    import re
    import subprocess
    root=Path(root).resolve(); logs=root/'controller_logs'; logs.mkdir(exist_ok=True)
    status_path=PRIVATE/'outputs/overnight_20261113/operator_status.json'
    packet=read(root/'packet_record.json')
    session='sol-head-policy-20261113-'+datetime.now(timezone.utc).strftime('%H%M%S')
    base=['C:/Users/Advait/.local/bin/colab.exe','--config',str(root/'sessions.json')]
    os.environ['PYTHONIOENCODING']='utf-8'
    record=dict(status='PLANNED',session=session,controller_pid=os.getpid(),packet=packet,events=[],failures=[],
        executed_script_sha256=sha(__file__),started_utc=datetime.now(timezone.utc).isoformat(),
        completed_stages=['A'] if packet.get('retained_stage_A_sha256') else [],
        estimate=dict(transfer_minutes=packet['estimated_transfer_minutes'],inference_minutes=25,
            last_rate_CU_hr=1.94,max_CU=20,max_allocated_seconds=21600,max_admission_CU_hr=6,
            upload_workers=1,chunk_bytes=4*1024**2,no_retry=True))
    started=None; allocated=False; operation_deadline=5*3600+30*60; balance=None; rate=None
    def elapsed(): return time.monotonic()-started if started else 0
    def save():
        tmp=root/'operation.tmp'; write(tmp,record); os.replace(tmp,root/'operation.json')
        state=dict(phase=record['status'],controller_pid=os.getpid(),owned_session=session if allocated else None,
            spend=dict(displayed_delta_CU=record.get('displayed_delta_CU'),admission_rate_CU_hr=rate,
                elapsed_allocated_seconds=elapsed(),estimated_elapsed_CU=elapsed()/3600*rate if rate else 0,
                cumulative_allocated_seconds=record.get('prior_cumulative_allocated_seconds',0)+elapsed(),
                cumulative_estimated_CU=record.get('prior_cumulative_CU',0)+(elapsed()/3600*rate if rate else 0)),
            completed_stages=record['completed_stages'],checkpoint_path=str(root/'results/checkpoint.json'),
            operation_path=str(root/'operation.json'),updated_utc=datetime.now(timezone.utc).isoformat(),
            teardown_verified=record.get('owned_teardown_verified',False))
        temp=status_path.with_suffix('.tmp'); write(temp,state); os.replace(temp,status_path)
    def call(args,label,timeout=90,check=True,deadline=None):
        cutoff=operation_deadline if deadline is None else deadline
        remaining=cutoff-elapsed()
        if remaining<=0: raise TimeoutError('host absolute deadline before '+label)
        p=subprocess.run(base+args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,encoding='utf-8',errors='replace',
            timeout=min(timeout,remaining))
        (logs/(label+'.log')).write_text(p.stdout,encoding='utf-8')
        if check and p.returncode: raise RuntimeError(label+' CLI returncode '+str(p.returncode))
        return p.stdout
    def remote(code,label,timeout=90,deadline=None,marker=None):
        path=root/(label+'.py'); path.write_text(code,encoding='utf-8')
        output=call(['exec','-s',session,'-f',str(path),'--timeout',str(int(timeout))],label,timeout+20,deadline=deadline)
        record['events'].append(dict(label=label,elapsed_seconds=elapsed())); save()
        if marker and marker not in output: raise RuntimeError(label+' missing remote success marker; inspect traceback')
        return output
    save()
    try:
        before=call(['usage'],'before_usage'); sessions=call(['sessions'],'before_sessions')
        balance=float(re.search(r'Current balance:\s*([\d.]+)',before).group(1))
        assert 'Active assignments: 0' in before,'another assignment; no competing allocation'
        assert balance>=20,'less than authorized20CU available'
        # Prior controllers, if any, consume the same cumulative envelope.
        previous=list(root.parent.glob('head_policy_20261113*/operation.json'))
        prior_seconds=prior_cost=0
        for path in previous:
            if path==root/'operation.json': continue
            old=read(path); assert old.get('owned_teardown_verified'),'prior ownership unresolved'
            prior_seconds+=old.get('elapsed_seconds',0)
            prior_cost+=max(old.get('displayed_delta_CU') or 0,old.get('elapsed_seconds',0)/3600*old.get('admission_rate_CU_hr',6))
        record.update(prior_cumulative_allocated_seconds=prior_seconds,prior_cumulative_CU=prior_cost)
        assert prior_seconds<21600 and prior_cost<20
        started=time.monotonic(); allocated=True; record['status']='ALLOCATING'; save()
        call(['new','-s',session,'--gpu','L4'],'allocate',180)
        usage=call(['usage'],'admission')
        rate=float(re.search(r'Usage rate:\s*([\d.]+)',usage).group(1))
        assert 0<rate<=6,'actual admission outside authorized rate'
        operation_deadline=min(21600-prior_seconds-15*60,(20-prior_cost-.3)/rate*3600-15*60)
        assert (packet['estimated_transfer_minutes']+35)*60<operation_deadline,'estimated work exceeds remaining envelope'
        record.update(admission_rate_CU_hr=rate,operation_deadline_seconds=operation_deadline,status='UPLOADING'); save()
        parts=sorted((root/'chunks').glob('part*'))
        def upload(part):
            output=call(['upload','-s',session,str(part),'/content/'+part.name],'upload_'+part.name,90)
            if 'Traceback' in output: raise RuntimeError('upload traceback '+part.name)
            return part.name
        # Serial 4MiB transfer matches the previously successful controller pattern.
        for j,part in enumerate(parts):
            upload(part)
            record['uploaded_chunks']=j+1;save()
            if j%80==0:print('UPLOAD',j+1,len(parts),'seconds',round(elapsed()),flush=True)
        record['status']='SETUP'; save()
        # Keep packed original script and exact executed replacement, with hashes.
        current=Path(__file__).read_text(encoding='utf-8')
        restore_code=''
        if packet.get('retained_stage_A_sha256'):
            restore_code="assert hashlib.sha256(Path('/content/packet/retained_stage_A.tar.gz').read_bytes()).hexdigest()=="+repr(packet['retained_stage_A_sha256'])+"\nwith tarfile.open('/content/packet/retained_stage_A.tar.gz') as saved: saved.extractall('/content/packet',filter='data')\n"
        remote("import subprocess,sys,tarfile,json,hashlib\nfrom pathlib import Path\n"
            "with open('/content/packet.tar','wb') as dest:\n    for part in sorted(Path('/content').glob('part*')): dest.write(part.read_bytes())\n"
            "assert hashlib.sha256(Path('/content/packet.tar').read_bytes()).hexdigest()=="+repr(packet['sha256'])+"\n"
            "with tarfile.open('/content/packet.tar') as t: t.extractall('/content',filter='data')\n"
            +restore_code+
            "r=Path('/content/packet/results');r.mkdir(exist_ok=True)\n"
            "Path('/content/packet/experiments/packed_mechanism.py').write_bytes(Path('/content/packet/experiments/2026-11-13_head_policy_mechanism.py').read_bytes())\n"
            "Path('/content/packet/experiments/2026-11-13_head_policy_mechanism.py').write_text("+repr(current)+",encoding='utf-8')\n"
            "(r/'executed_script.py').write_text("+repr(current)+",encoding='utf-8')\n"
            "assert hashlib.sha256(Path('/content/packet/config.json').read_bytes()).hexdigest()=="+repr(packet['config_sha256'])+"\n"
            "p=subprocess.run([sys.executable,'-m','pip','install','--quiet','ultralytics==8.4.197'],capture_output=True,text=True)\n"
            "(r/'install.txt').write_text(p.stdout+p.stderr)\n(r/'install_status.json').write_text(json.dumps({'returncode':p.returncode}))\n"
            "assert p.returncode==0\nprint('REMOTE_READY')\n",'setup',420,marker='REMOTE_READY')
        record['status']='INFERENCE'; save()
        child_seconds=int(min(2700,operation_deadline-elapsed()-180))
        assert child_seconds>=300,'no inference/retrieval margin'
        remote("import subprocess,sys,json,time\nfrom pathlib import Path\nr=Path('/content/packet/results')\n"
            "with open(r/'inference.log','w') as log:\n    try:\n"
            "        p=subprocess.run([sys.executable,'/content/packet/experiments/2026-11-13_head_policy_mechanism.py','infer','/content/packet'],stdout=log,stderr=subprocess.STDOUT,timeout="+str(child_seconds)+")\n"
            "        rc=p.returncode\n    except subprocess.TimeoutExpired: rc=-124\n"
            "(r/'process_status.json').write_text(json.dumps({'returncode':rc}))\nprint('DIRECT_CHILD_STATUS',rc)\n",'infer_blocking',child_seconds+30,marker='DIRECT_CHILD_STATUS')
        record['status']='RETRIEVING'; save()
    except BaseException as exc:
        record['status']='ERROR'; record['failures'].append(repr(exc)); save(); print('ERROR',repr(exc),flush=True)
    finally:
        if allocated:
            cleanup=min(21600-record.get('prior_cumulative_allocated_seconds',0),
                (20-record.get('prior_cumulative_CU',0))/rate*3600 if rate else 21600)
            try:
                remote("from pathlib import Path\nimport tarfile\nr=Path('/content/packet/results');r.mkdir(parents=True,exist_ok=True)\n"
                    "with tarfile.open('/content/evidence.tar.gz','w:gz') as t: t.add(r,arcname='results')\n"
                    "print('EVIDENCE_PACKED',Path('/content/evidence.tar.gz').stat().st_size)\n",'retrieve_pack',120,cleanup-300,marker='EVIDENCE_PACKED')
                call(['download','-s',session,'/content/evidence.tar.gz',str(root/'evidence_final.tar.gz')],'retrieve_download',180,deadline=cleanup-120)
                with tarfile.open(root/'evidence_final.tar.gz') as archive: archive.extractall(root,filter='data')
                record['evidence_sha256']=sha(root/'evidence_final.tar.gz')
            except BaseException as exc: record['retrieval_error']=repr(exc); save()
            try: call(['log','-s',session,'-o',str(root/'history.jsonl')],'retrieve_history',30,False,cleanup-100)
            except BaseException as exc: record['history_error']=repr(exc)
            try: call(['stop','-s',session],'stop_owned',70,deadline=cleanup-25)
            except BaseException as exc: record['stop_error']=repr(exc)
            try:
                sessions=call(['sessions'],'verify_sessions',15,deadline=cleanup-10)
                usage=call(['usage'],'final_usage',10,deadline=cleanup)
                record['owned_teardown_verified']=session not in sessions and 'Active assignments: 0' in usage
                match=re.search(r'Current balance:\s*([\d.]+)',usage)
                record.update(displayed_balance_before_CU=balance,displayed_balance_after_CU=float(match.group(1)) if match else None,
                    displayed_delta_CU=round(balance-float(match.group(1)),2) if match and balance else None)
            except BaseException as exc: record['teardown_error']=repr(exc)
        record.update(elapsed_seconds=elapsed(),ended_utc=datetime.now(timezone.utc).isoformat())
        try:
            assert read(root/'results/process_status.json')['returncode']==0,'remote child failed'
            assert read(root/'results/inference_complete.json')['status']=='COMPLETE'
            assert record['owned_teardown_verified']
            record.update(status='COMPLETE',completed_stages=['A','B'])
        except BaseException as exc: record['failures'].append(repr(exc)); record['status']='ERROR'
        save(); print('FINAL',json.dumps({k:v for k,v in record.items() if k not in ('events','packet')}),flush=True)


def aggregate(root,destination,only_stage=None):
    """Reuse the established evaluator; publish counts, keep identities private."""
    root=Path(root); result=root/'results'; cfg=read(root/'packet/config.json')
    manifests={s:read(root/f'packet/manifest_{s}.json') for s in ('A','B')}
    if only_stage is not None: manifests={only_stage:manifests[only_stage]}
    a_ids={i['image_id'] for p in manifests['A']['panels'].values() for i in p['images']}
    all_ids={i['image_id'] for m in manifests.values() for p in m['panels'].values() for i in p['images']}
    raw={cell:dict(schema_version=pilot.PY_SCHEMA,predictions=[],degenerate_predictions=[],
        provenance=dict(evaluated_image_ids=[])) for cell in cfg['cells']}
    evidence={}; checks={}; controls={}; coverage_private={}
    for h in ('o2o','o2m'):
        status=read(result/f'{h}_status.json'); assert status['status']=='COMPLETE'
        seen=[]; native_checks=[]; hashes=[]; counts=collections.Counter(); limits={}
        corrections={}
        correction_dir=result/'correction_last_native_batch'
        if (correction_dir/f'{h}_batch_0000.json').exists():
            assert read(correction_dir/'process_status.json')['returncode']==0
            correction_batch=read(correction_dir/f'{h}_batch_0000.json'); assert correction_batch['validated']
            for j,iid in enumerate(correction_batch['image_ids']):
                corrections[iid]=dict(native=correction_batch['native'][j],cells={p:rows[j] for p,rows in correction_batch['cells'].items()})
            native_checks.extend(correction_batch['native_checks'])
            hashes.append(dict(correction_batch_sha256=sha(correction_dir/f'{h}_batch_0000.json'),
                raw_boxes=correction_batch['stage']['raw_box_sha256'],raw_scores=correction_batch['stage']['raw_scores_sha256'],
                decoded=correction_batch['stage']['decoded_sha256'],input=correction_batch['stage']['input_sha256']))
        for path in sorted(result.glob(f'{h}_batch_*.json')):
            batch=read(path); assert batch['validated']; seen.extend(batch['image_ids'])
            native_checks.extend(batch['native_checks'])
            hashes.append(dict(batch_sha256=sha(path),raw_boxes=batch['stage']['raw_box_sha256'],
                raw_scores=batch['stage']['raw_scores_sha256'],decoded=batch['stage']['decoded_sha256'],input=batch['stage']['input_sha256']))
            for policy in ('K','N'):
                if policy not in batch['cells']: continue
                cell=h+'_'+policy
                rows=batch['native'] if (h,policy) in (('o2o','K'),('o2m','N')) else batch['cells'][policy]
                for iid,values in zip(batch['image_ids'],rows):
                    if (h,policy) not in (('o2o','K'),('o2m','N')) and iid not in a_ids: continue
                    if iid in corrections:
                        values=corrections[iid]['native'] if (h,policy) in (('o2o','K'),('o2m','N')) else corrections[iid]['cells'][policy]
                    raw[cell]['provenance']['evaluated_image_ids'].append(iid)
                    counts[cell]+=len(values)
                    lim=limits.setdefault(cell,dict(max_emitted_per_image=0,images_at_final_cap3000=0,zero_area=0))
                    lim['max_emitted_per_image']=max(lim['max_emitted_per_image'],len(values))
                    lim['images_at_final_cap3000']+=len(values)==3000
                    for j,(x1,y1,x2,y2,score,cls) in enumerate(values):
                        assert cls==0
                        pred=dict(candidate_id=iid+f':{j:04d}',image_id=iid,category='human',bbox=[x1,y1,x2-x1,y2-y1],score=score)
                        if x1==x2 or y1==y2:
                            raw[cell]['degenerate_predictions'].append(dict(**pred,native_xyxy=[x1,y1,x2,y2])); lim['zero_area']+=1
                        else: raw[cell]['predictions'].append(pred)
        assert len(seen)==len(set(seen))==len(all_ids) and set(seen)==all_ids
        controls[h]=dict(images=len(seen),replay_pass=all(c['shape_equal'] and c['classes_equal'] and
            c['max_box_error']<=.002 and c['max_score_error']<=1e-6 for c in native_checks),
            exact_counts_classes=all(c['shape_equal'] and c['classes_equal'] for c in native_checks),
            max_box_error=max((c['max_box_error'] or 0) for c in native_checks),
            max_score_error=max((c['max_score_error'] or 0) for c in native_checks),
            mismatched_images=sum(not(c['shape_equal'] and c['classes_equal'] and c['max_box_error']<=.002 and c['max_score_error']<=1e-6) for c in native_checks))
        controls[h]['all_replay_values_exact']=controls[h]['exact_counts_classes'] and controls[h]['max_box_error']==0 and controls[h]['max_score_error']==0
        controls[h]['replay_metric_counts_exact']=controls[h]['all_replay_values_exact']
        controls[h]['original_batch_correction_image_heads']=len(corrections)
        evidence[h]=dict(status=status,batch_files=len(hashes),stage_inputs_config_sha256=hashlib.sha256(
            json.dumps(dict(config_sha256=sha(root/'packet/config.json'),batches=hashes),sort_keys=True).encode()).hexdigest(),
            candidates=dict(counts),realized_limits=limits,
            raw_debug_files=[dict(path=str(p),sha256=sha(p),bytes=p.stat().st_size) for p in result.glob(h+'_debug_*.pt')])
        stage_status_paths=[root/'probe/results'/f'{h}_status.json',root/'stage_A/results'/f'{h}_status.json',
            result/'correction_last_native_batch'/f'{h}_status.json',result/f'{h}_status.json']
        evidence[h]['peak_allocated_bytes_across_stages']=max(read(p).get('peak_allocated_bytes',0) for p in stage_status_paths if p.exists())
        evidence[h]['peak_reserved_bytes_across_stages']=max(read(p).get('peak_reserved_bytes',0) for p in stage_status_paths if p.exists())
    operation=read(root/'operation.json')
    output=dict(researcher='GPT Sol',G0='PENDING',config=cfg,stages={},controls=controls,
        provenance=dict(private_root=str(root),packet=read(root/'packet_record.json'),
            operation={k:v for k,v in operation.items() if k not in ('packet','events','session')},
            process_status=read(result/('stage_A_process_status.json' if only_stage=='A' else 'process_status.json')),
            evidence_sha256=sha(root/('stage_A_evidence.tar.gz' if only_stage=='A' else 'evidence_final.tar.gz')),
            executed_inference_sha256=sha(result/('stage_A_executed_script.py' if only_stage=='A' else 'executed_script.py')),aggregation_sha256=sha(__file__),
            evaluator_sha256=sha(REPO/'src/threshold_transfer/metrics.py'),
            implementation={p.name:sha(p) for p in result.glob('*_source.py')},runtime=evidence))
    output['provenance']['executed_stages_scripts']={p.name:sha(p) for p in result.glob('*executed_script.py')}
    output['provenance']['host_controller_initial_sha256']=sha(root/'controller_initial.py')
    assert output['provenance']['host_controller_initial_sha256']==operation['executed_script_sha256']
    output['provenance']['early_stage_host_scripts']={p.name:sha(p) for p in root.glob('*_host.py')}
    output['provenance']['actual_peer_exchange_sha256']=sha(root/'actual_peer_exchange.json')
    if (root/'previous_operation.json').exists():
        previous=read(root/'previous_operations.json') if (root/'previous_operations.json').exists() else [read(root/'previous_operation.json')]
        output['provenance']['previous_operations']=[{k:p.get(k) for k in ('status','failures','owned_teardown_verified',
            'elapsed_seconds','admission_rate_CU_hr','displayed_delta_CU','evidence_sha256')} for p in previous]
        output['provenance']['previous_operations_sha256']=sha(root/'previous_operations.json') if (root/'previous_operations.json').exists() else sha(root/'previous_operation.json')
        output['provenance']['execution_totals']=dict(allocations=len(previous)+1,
            cumulative_allocated_seconds=sum(p['elapsed_seconds'] for p in previous)+operation['elapsed_seconds'],
            displayed_delta_CU=round(sum(p['displayed_delta_CU'] for p in previous)+operation['displayed_delta_CU'],2),
            elapsed_rate_estimate_CU=(sum(p['elapsed_seconds']*p['admission_rate_CU_hr'] for p in previous)+
                operation['elapsed_seconds']*operation['admission_rate_CU_hr'])/3600,
            all_owned_teardown_verified=all(p['owned_teardown_verified'] for p in previous) and operation['owned_teardown_verified'])
        output['provenance']['prior_stage_host_scripts']={str(p):sha(p) for p in (PRIVATE/'outputs/colab/head_policy_20261113').glob('*_host.py')}
        assert output['provenance']['execution_totals']['cumulative_allocated_seconds']<=21600
        assert output['provenance']['execution_totals']['elapsed_rate_estimate_CU']<=20
    if (root/'stage_B_prefix_attempt.json').exists():
        output['provenance']['cancelled_auxiliary_prefix_attempt']=read(root/'stage_B_prefix_attempt.json')
    if (result/'correction_last_native_batch/prespecified_correction.json').exists():
        request=read(result/'correction_last_native_batch/prespecified_correction.json')
        output['provenance']['single_original_batch_correction']={k:v for k,v in request.items() if k!='original_H4_final_batch_ids'}
        output['provenance']['single_original_batch_correction'].update(image_count=len(request['original_H4_final_batch_ids']),
            evidence_sha256=sha(root/'correction_evidence.tar.gz'),request_sha256=sha(root/'native_batch_correction.json'),
            executed_script_sha256=sha(result/'correction_last_native_batch/correction_executed_script.py'),
            first_pass_aggregate_sha256=sha(root/'stage_A_first_pass_aggregate.json'),
            first_pass_controls=read(root/'stage_A_first_pass_aggregate.json')['controls'])
        output['provenance']['single_original_batch_correction']['original_five_image_output_checks']=read(root/'correction_vs_original.json')
    if (root/'historical_output_controls.json').exists():
        output['provenance']['historical_positional_array_diagnostic']=dict(
            result=read(root/'historical_output_controls.json'),sha256=sha(root/'historical_output_controls.json'),
            interpretation='Historical per-position rows differ across run/batch contexts; this is distinct from exact current-forward native selector replay. No historical tensor identity is claimed.')
    assert output['provenance']['process_status']['returncode']==0
    old_aggregate=read(REPO/'docs/gpt/2026-11-11_sol_dual_head_transfer.json')
    def compact(point):
        if point is None: return None
        return {k:point[k] for k in ('threshold','image_count','eligible_gt','retained_candidates','tp','fp','ignored','fn','recall','precision','fppi')} | dict(
            native_zero_area_fp=sum(r.get('native_zero_area',False) for r in point['matches']))
    def covered(point): return {r['annotation_id'] for r in point['matches'] if r['outcome']=='TP'} if point else None
    def diff(a,b):
        if a is None or b is None: return None
        return dict(tp=a['tp']-b['tp'],fp=a['fp']-b['fp'],
            recall=a['recall']['value']-b['recall']['value'] if a['recall']['value'] is not None and b['recall']['value'] is not None else None,
            fppi=a['fppi']['value']-b['fppi']['value'] if a['fppi']['value'] is not None and b['fppi']['value'] is not None else None)
    def set_contrast(a,b,ca,cb):
        if a is None or b is None: return None
        return dict(shared=len(a&b),only_first=len(a-b),only_second=len(b-a),
            first_only_in_second_ceiling=len((a-b)&cb),first_only_absent_second_ceiling=len((a-b)-cb),
            second_only_in_first_ceiling=len((b-a)&ca),second_only_absent_first_ceiling=len((b-a)-ca))
    for stage,manifest in manifests.items():
        cells=cfg['cells'] if stage=='A' else ['o2o_K','o2m_N']
        stage_result=dict(panels={},cells={},contrasts={},coverage={})
        sets={}; ceiling_sets={}
        for cell in cells:
            h=cell.split('_')[0]; source=pilot.pilot_evaluator(manifest['panels']['source_selection'],raw[cell])
            selected=source.select_threshold(.9)
            source_compact={k:v for k,v in selected.items() if k not in ('operating_point','candidate_ceiling')}
            source_compact['operating_point']=compact(selected['operating_point'])
            source_compact['candidate_ceiling']=compact(selected['candidate_ceiling'])
            stage_result['cells'][cell]=dict(source_selection=source_compact,panels={})
            sets[cell]={}; ceiling_sets[cell]={}
            for name,panel in manifest['panels'].items():
                ev=source if name=='source_selection' else pilot.pilot_evaluator(panel,raw[cell])
                ceiling=ev.operating_point(); direct=ev.operating_point(cfg['original_thresholds'][h])
                reselected=ev.operating_point(selected['threshold']) if selected['status']=='FEASIBLE' else None
                ceiling_sets[cell][name]=covered(ceiling)
                sets[cell][name]=dict(direct=covered(direct),reselected=covered(reselected))
                stage_result['cells'][cell]['panels'][name]=dict(ceiling=compact(ceiling),direct=compact(direct),reselected=compact(reselected),
                    boundary_movement=diff(reselected,direct))
                stage_result['panels'][name]=dict(images=len(panel['images']),gt=ev.gt_count,
                    crowd=sum(a['iscrowd'] for a in panel['annotations']),
                    native_gt_categories=dict(collections.Counter(a['attributes']['pilot_native_category'] for a in panel['annotations'] if not(a['ignore'] or a['iscrowd']))))
        pairs=[('native','o2o_K','o2m_N')]
        if stage=='A': pairs += [('head_K','o2o_K','o2m_K'),('head_N','o2o_N','o2m_N'),
            ('policy_o2o','o2o_K','o2o_N'),('policy_o2m','o2m_K','o2m_N')]
        for label,first,second in pairs:
            contrasts={}; gt_contrasts={}
            for name in manifest['panels']:
                a,b=(stage_result['cells'][c]['panels'][name] for c in (first,second))
                ca,cb=(ceiling_sets[c][name] for c in (first,second))
                contrasts[name]={mode:diff(a[mode],b[mode]) for mode in ('direct','reselected','ceiling')}
                gt_contrasts[name]=dict(ceiling=set_contrast(ca,cb,ca,cb),**{
                    mode:set_contrast(sets[first][name][mode],sets[second][name][mode],ca,cb) for mode in ('direct','reselected')})
            contrasts['night_minus_coco_reference']={mode:{key:(contrasts['night'][mode][key]-contrasts['coco_reference'][mode][key]
                if contrasts['night'][mode] is not None and contrasts['coco_reference'][mode] is not None and
                contrasts['night'][mode][key] is not None and contrasts['coco_reference'][mode][key] is not None else None)
                for key in ('recall','fppi')} for mode in ('direct','reselected','ceiling')}
            stage_result['contrasts'][label]=dict(first=first,second=second,panels=contrasts)
            stage_result['coverage'][label]=gt_contrasts
        if stage=='A':
            stage_result['contrasts']['interaction']={name:{mode:{key:(
                stage_result['contrasts']['head_K']['panels'][name][mode][key]-stage_result['contrasts']['head_N']['panels'][name][mode][key]
                if stage_result['contrasts']['head_K']['panels'][name][mode] is not None and stage_result['contrasts']['head_N']['panels'][name][mode] is not None and
                stage_result['contrasts']['head_K']['panels'][name][mode][key] is not None and stage_result['contrasts']['head_N']['panels'][name][mode][key] is not None else None)
                for key in ('recall','fppi')} for mode in ('direct','reselected','ceiling')} for name in manifest['panels']}
            interaction=stage_result['contrasts']['interaction']
            interaction['night_minus_coco_reference']={mode:{key:(interaction['night'][mode][key]-interaction['coco_reference'][mode][key]
                if interaction['night'][mode][key] is not None and interaction['coco_reference'][mode][key] is not None else None)
                for key in ('recall','fppi')} for mode in ('direct','reselected','ceiling')}
            # Direct swap plus within-cell boundary movement = total swap/reselection.
            stage_result['additive_count_checks']={}
            for h,native in (('o2o','K'),('o2m','N')):
                other='N' if native=='K' else 'K'; by_panel={}
                for name in manifest['panels']:
                    a=stage_result['cells'][h+'_'+native]['panels'][name]
                    b=stage_result['cells'][h+'_'+other]['panels'][name]
                    direct=diff(b['direct'],a['direct']); movement=diff(b['reselected'],b['direct']); total=diff(b['reselected'],a['direct'])
                    by_panel[name]=dict(direct_swap=direct,boundary_movement=movement,total=total,
                        exact_TP_FP_identity=all(direct[k]+movement[k]==total[k] for k in ('tp','fp')) if movement is not None else None)
                    assert by_panel[name]['exact_TP_FP_identity'] is not False
                stage_result['additive_count_checks'][h]=by_panel
            historical={}
            for h,cell in (('o2o','o2o_K'),('o2m','o2m_N')):
                old=old_aggregate['heads']['yolo26s_'+h]
                historical[h]={name:{mode:all(stage_result['cells'][cell]['panels'][name][mode][k]==old['panels'][name][oldmode][k] for k in ('tp','fp','ignored'))
                    for mode,oldmode in (('direct','operating'),('ceiling','ceiling'))} for name in manifest['panels']}
                controls[h]['historical_H4_all_metric_counts_exact']=all(all(x.values()) for x in historical[h].values())
            stage_result['historical_H4_controls']=historical
            stage_result['swapped_interpretation_supported']=all(c['replay_pass'] and c['replay_metric_counts_exact'] and c['historical_H4_all_metric_counts_exact'] for c in controls.values())
        coverage_private[stage]=dict(operating={c:{n:{m:sorted(v) if v is not None else None for m,v in modes.items()} for n,modes in panels.items()} for c,panels in sets.items()},
            ceiling={c:{n:sorted(v) for n,v in panels.items()} for c,panels in ceiling_sets.items()})
        output['stages'][stage]=stage_result
    write(root/'coverage_private.json',coverage_private)
    output['provenance']['private_GT_crosswalk_sha256']=sha(root/'coverage_private.json')
    write(destination,output)
    print(json.dumps(dict(controls=controls,stages={s:{k:v for k,v in x['contrasts']['native']['panels']['night'].items()} for s,x in output['stages'].items()})))


def finalize_saved(root,destination):
    """CPU-only finalization after the GPT Sol coordinator's transport stop; no new inference."""
    root=Path(root);aggregate(root,destination,only_stage='A');data=read(destination)
    attempts=[root,root.with_name(root.name+'_recovery')]
    operations=[read(p/'operation.json') for p in attempts]
    assert all(o['owned_teardown_verified'] for o in operations)
    data['completion']='STAGE_A_COMPLETE_STAGE_B_INCOMPLETE_BLOCKED'
    data['stages']['A']['status']='COMPLETE'
    planned=read(root/'packet/manifest_B.json')['panels']
    data['stages']['B']=dict(status='INCOMPLETE_BLOCKED',results=None,completed_new_image_heads=0,
        planned_unique_images=2912,planned_new_train_images=1600,planned_new_reference_images=800,
        unchanged_COCO_source_reference_images=512,manifest_sha256=sha(root/'packet/manifest_B.json'),
        planned_panel_images={n:len(p['images']) for n,p in planned.items()},
        reason='Initial upload connection reset; one serial recovery lost its runtime404/401. No expanded inference completed. The GPT Sol coordinator stopped transport development and further allocation.',
        selection='Prespecified all-image panel; not dropped based on Stage A favorability')
    data['provenance']['execution_totals']=dict(allocations=len(operations),
        cumulative_allocated_seconds=sum(o['elapsed_seconds'] for o in operations),
        displayed_delta_CU=round(sum(o['displayed_delta_CU'] for o in operations),2),
        elapsed_rate_estimate_CU=sum(o['elapsed_seconds']*o['admission_rate_CU_hr'] for o in operations)/3600,
        all_owned_teardown_verified=True,stage_A_unique_image_cells=933*4,
        native_image_head_evaluations=933*2+5*2,correction_image_cells=5*4,
        stage_B_completed_new_image_heads=0,counts_exclude_native_warmup=True)
    data['provenance']['transport_attempts']=[]
    for p,o in zip(attempts,operations):
        log=p/'controller_logs'/('upload_part1373.log' if p==root else 'upload_part0198.log')
        data['provenance']['transport_attempts'].append(dict(private_root=str(p),operation_sha256=sha(p/'operation.json'),
            controller_sha256=sha(p/'controller_initial.py'),failed_upload_log_sha256=sha(log),
            **{k:o.get(k) for k in ('status','failures','uploaded_chunks','owned_teardown_verified','retrieval_error',
                'displayed_delta_CU','elapsed_seconds','admission_rate_CU_hr','evidence_sha256')}))
        assert sha(p/'controller_initial.py')==o['executed_script_sha256']
    data['provenance']['retained_combined_A_archive_sha256']=sha(root/'evidence_final.tar.gz')
    unexecuted=root.with_name(root.name+'_streamed')/'unexecuted_status.json'
    data['provenance']['unexecuted_transport_development']=read(unexecuted)
    data['control_scope']=dict(current_forward_native_replay='Official native predictor versus reconstructed selectors on the same forward inputs; exact boxes/scores/classes/counts.',
        historical_H4='TP/FP/ignored at original native thresholds and ceiling, all14 panels; corrected final batch5.',
        original_final_batch5='Both corrected heads match the original five native arrays exactly.',
        broader_historical_arrays='Per-position comparison differs; no permutation-invariant matching or full historical tensor identity established.')
    for h,entry in data['provenance']['runtime'].items():
        batches=entry['status'].pop('batches',[])
        entry['status']['logged_batches']=len(batches)
        entry['status']['logged_batch_seconds']=sum(b['seconds'] for b in batches)
        records=[read(p) for p in sorted((root/'results').glob(f'{h}_batch_*.json'))]
        first=records[0]['stage'];other='o2m' if h=='o2o' else 'o2o'
        entry['native_branch_evidence']={k:first[k] for k in ('format','branch_calls','backend_end2end','head_end2end','head_max_det','branches_after','input_shape')}
        entry['all_primary_batches_correct_branch']=all(b['stage']['branch_calls'][h]>0 and b['stage']['branch_calls'][other]==0 for b in records)
        assert entry['all_primary_batches_correct_branch']
        data['controls'][h]['replay_image_evaluations']=933+5
    assert data['provenance']['execution_totals']['cumulative_allocated_seconds']<=21600
    assert data['provenance']['execution_totals']['elapsed_rate_estimate_CU']<=20
    write(destination,data)


def figures(root,destination):
    """Measured finite-panel figures, no inferred error bars or independence."""
    root=Path(root); sys.path.insert(0,str(root/'plotdeps'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
    import numpy as np
    data=read(destination); folder=Path(destination).parent
    prefix='2026-11-13_sol_head_policy_'
    colors=['#20639b','#ed8b23','#19745d','#b34d72']
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,
        'axes.spines.right':False,'svg.fonttype':'none','figure.facecolor':'white'})
    def save(fig,name):
        for ext in ('png','svg'): fig.savefig(folder/(prefix+name+'.'+ext),dpi=180,bbox_inches='tight')
        plt.close(fig)
    a=data['stages']['A']; cells=data['config']['cells']
    fig,axes=plt.subplots(2,2,figsize=(11,7),layout='constrained')
    x=np.arange(4)
    for col,(mode,label) in enumerate((('direct','Original head-specific thresholds'),('reselected','Cell-specific source .90 reselection'))):
        for shift,name in ((-.16,'coco_reference'),(.16,'night')):
            values=[a['cells'][c]['panels'][name][mode] for c in cells]
            axes[0,col].bar(x+shift,[100*v['recall']['value'] if v is not None else float('nan') for v in values],width=.3,
                color=colors[0] if name=='coco_reference' else colors[1],label='COCO reference' if name=='coco_reference' else 'Night')
            axes[1,col].bar(x+shift,[v['fppi']['value'] if v is not None else float('nan') for v in values],width=.3,
                color=colors[0] if name=='coco_reference' else colors[1])
            for j,v in enumerate(values):
                if v is not None: axes[0,col].text(j+shift,100*v['recall']['value']+1,f"{v['tp']}/{v['eligible_gt']}",ha='center',fontsize=8,rotation=45)
        axes[0,col].set(title=label,ylabel='Recall (%)',ylim=(0,110))
        axes[1,col].set(ylabel='False positives / image')
        for ax in axes[:,col]: ax.set_xticks(x,[c.replace('_',' / ') for c in cells]); ax.grid(axis='y',alpha=.16); ax.set_axisbelow(True)
    axes[0,0].legend(frameon=False,fontsize=9)
    fig.suptitle('Stage A: learned head × native postprocessing bundle\nK: all-class top-k; N: argmax/person filter/NMS .70 | frozen H4 panel',fontsize=13)
    save(fig,'factorial')
    if 'B' in data['stages'] and 'cells' in data['stages']['B']:
        b=data['stages']['B']; panels=['coco_reference','fog','fog_normal','night','night_normal','rain','rain_normal','snow','snow_normal']
        labels=['COCO ref','Fog','Fog ref','Night','Night ref','Rain','Rain ref','Snow','Snow ref']
        fig,axes=plt.subplots(2,1,figsize=(12,7),sharex=True,layout='constrained'); x=np.arange(len(panels))
        for color,cell,label in ((colors[0],'o2o_K','O2O + K'),(colors[1],'o2m_N','O2M + N')):
            vals=[b['cells'][cell]['panels'][n]['direct'] for n in panels]
            axes[0].plot(x,[100*v['recall']['value'] for v in vals],'o-',color=color,label=label)
            axes[0].scatter(x,[100*b['cells'][cell]['panels'][n]['ceiling']['recall']['value'] for n in panels],marker='^',color=color,s=35,alpha=.6)
            axes[1].plot(x,[v['fppi']['value'] for v in vals],'o-',color=color)
        axes[0].set(ylabel='Recall (%)',ylim=(0,105)); axes[0].legend(frameon=False,ncol=2)
        axes[1].set(ylabel='False positives / image',xticks=x,xticklabels=labels)
        for ax in axes: ax.grid(axis='y',alpha=.18)
        for j,name in enumerate(panels):
            p=b['panels'][name]; axes[1].text(j,-.21,f"n={p['images']}\nGT={p['gt']}",ha='center',transform=axes[1].get_xaxis_transform(),fontsize=8)
        fig.suptitle('Stage B: expanded finite ACDC train panel, original source thresholds\nCircles: operating recall; triangles: frozen candidate ceiling. Train/val recordings overlap.',fontsize=13)
        save(fig,'replication')
    fig,ax=plt.subplots(figsize=(12,4)); ax.set(xlim=(0,12),ylim=(0,4)); ax.axis('off')
    def box(x,y,w,h,label,color):
        ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=.08',facecolor=color,edgecolor='#354455',linewidth=1))
        ax.text(x+w/2,y+h/2,label,ha='center',va='center',fontsize=8.5)
    def arrow(a,b): ax.add_patch(FancyArrowPatch(a,b,arrowstyle='-|>',mutation_scale=12,color='#354455'))
    box(.1,1.45,1.6,1.1,'Native letterbox\n1280, FP32\nfrozen checkpoint','#e7edf3')
    box(2.1,2.5,1.8,.8,'Learned O2O head\ndecoded xyxy','#d8e9f4')
    box(2.1,.7,1.8,.8,'Learned O2M head\ndecoded xywh','#f9e7ce')
    box(4.5,2.45,3,1,'K bundle\nAll-class anchor top-k → class top-k\ncap3000 → person/floor filter','#deeee6')
    box(4.5,.65,3,1,'N bundle\nArgmax → person/floor filter\nmax_nms 30,000 → NMS .70\nfinal cap 3,000','#f4dfe6')
    box(8.2,1.4,1.5,1.2,'Official scale_boxes\noriginal coordinates\nthen clipping','#e7edf3')
    box(10.2,1.4,1.6,1.2,'Existing evaluator\nsource-only .90 rule\nrecall / FPPI / GT sets','#e7edf3')
    arrow((1.7,2),(2.1,2.9)); arrow((1.7,2),(2.1,1.1))
    for yy in (2.9,1.1):
        for zz in (2.95,1.15): arrow((3.9,yy),(4.5,zz))
    arrow((7.5,2.95),(8.2,2)); arrow((7.5,1.15),(8.2,2)); arrow((9.7,2),(10.2,2))
    ax.text(6,.05,'Conceptual diagram. Clone tensors; official xyxy↔xywh conversion before selector; NMS before clipping.\nStage A executed; Stage B planned native replication is blocked. No training or target tuning.',ha='center',fontsize=9)
    fig.suptitle('Frozen learned heads × complete native selection bundles',fontsize=13)
    save(fig,'pipeline')


if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('action',choices=['prepare','prepare_recovery','infer','infer_A','correct_native_batch','probe','operate','aggregate','aggregate_A','finalize_saved','figures']); p.add_argument('root'); p.add_argument('--destination'); args=p.parse_args()
    if args.action=='aggregate': aggregate(args.root,args.destination)
    elif args.action=='aggregate_A': aggregate(args.root,args.destination,only_stage='A')
    elif args.action=='finalize_saved': finalize_saved(args.root,args.destination)
    elif args.action=='figures': figures(args.root,args.destination)
    elif args.action=='probe': infer(args.root,limit_images=8)
    elif args.action=='infer_A': infer(args.root,limit_images=933)
    elif args.action=='correct_native_batch': infer(args.root,correction=True)
    else: {'prepare':prepare,'prepare_recovery':prepare_recovery,'infer':infer,'operate':operate}[args.action](args.root)
