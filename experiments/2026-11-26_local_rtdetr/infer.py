"""GPT Sol: local paths and bounded-memory saving for the frozen native policy."""
import argparse
import json
import time
import numpy as np
from PIL import Image
import torch
import torchvision.transforms as T
from local import OUT, OLD, configure, load, save, sha


def infer(arm, batch):
    cfg = configure(batch, 5, arm)
    checkpoint = OUT/arm/'last.pth'
    state = torch.load(checkpoint,map_location='cpu',weights_only=False)
    model = cfg.model
    model.load_state_dict(state['ema']['module'],strict=True)
    del state
    model = model.deploy().to('cuda').eval()
    post = cfg.postprocessor.deploy().to('cuda')
    selection = load(OLD/'manifest_selection.json')
    names = list(selection)+sorted(load(OLD/'manifest_val.json'))
    selection = set(selection)
    transforms = T.Compose([T.Resize((640,640)),T.ToTensor()])
    native = OUT/f'{arm}_native'
    native.mkdir(exist_ok=True)
    pboxes,pscores,offsets = [],[],[0]
    start = time.time()
    chunks = []
    with torch.inference_mode():
        for begin in range(0,len(names),batch):
            chunk = names[begin:begin+batch]
            inputs = []
            for name in chunk:
                split = 'train' if name in selection else 'val'
                with Image.open(OUT/f'data/images/{split}/{name}.jpg') as im:
                    inputs.append(transforms(im.convert('RGB')))
            output = model(torch.stack(inputs).to('cuda'))
            lab,box,score = post(output,torch.tensor([[1280,720]]*len(chunk),device='cuda'))
            idx = output['pred_logits'].sigmoid().flatten(1).topk(300,dim=-1).indices//10
            assert bool(torch.isfinite(box).all() and torch.isfinite(score).all())
            box,score,lab = box.cpu().numpy(),score.cpu().numpy(),lab.cpu().numpy()
            path = native/f'{begin:05d}.npz'
            np.savez_compressed(path,names=np.asarray(chunk),boxes=box,scores=score,labels=lab,
                     query_ids=idx.cpu().numpy(),logits=output['pred_logits'].cpu().numpy(),
                     raw_boxes=output['pred_boxes'].cpu().numpy())
            chunks.append(dict(file=path.name,sha256=sha(path),images=len(chunk)))
            for b,s,l in zip(box,score,lab):
                keep = (l==0)&(s>=1e-4)
                pboxes.append(b[keep]); pscores.append(s[keep]); offsets.append(offsets[-1]+int(keep.sum()))
            if begin%1600==0:
                save(arm+'_inference_progress.json',dict(images=begin+len(chunk),seconds=time.time()-start))
    path = OUT/f'{arm}_pedestrian.npz'
    np.savez_compressed(path,names=np.asarray(names),boxes=np.concatenate(pboxes),
                        scores=np.concatenate(pscores),offsets=np.asarray(offsets),
                        all_class_candidates=np.full(len(names),300))
    save(arm+'_inference.json',dict(status='PASS',images=len(names),seconds=time.time()-start,
         pedestrian_sha256=sha(path),checkpoint_sha256=sha(checkpoint),native_chunks=chunks,
         pedestrian_candidates=offsets[-1],native_candidates_per_image=300))


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--arm',required=True)
    p.add_argument('--batch',type=int,required=True)
    a=p.parse_args()
    infer(a.arm,a.batch)
