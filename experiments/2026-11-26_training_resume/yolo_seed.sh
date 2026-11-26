#!/bin/bash
# Claude Opus: exact YOLO11s 1280 px seed repeat (BDD amendment 5). Usage: yolo_seed.sh ID SEED
# Colab system Python; frozen remote.py stages; stops at the first failure.
ID=$1; SEED=$2
E=/content/yevidence; mkdir -p $E /content/preds
cd /content
run() {
  local name=$1; shift
  echo "$(date -u +%FT%TZ) START $name" >> $E/queue.log
  if "$@" > $E/$name.log 2>&1; then echo "$(date -u +%FT%TZ) PASS $name" >> $E/queue.log
  else echo "$(date -u +%FT%TZ) FAIL $name" >> $E/queue.log; touch $E/FAIL_$ID; exit 1; fi
}
run env_$ID bash /content/ypacket/yolo_env.sh
if [ -e /content/images.zip ] && [ ! -e /content/bdd100k_images_100k.zip ]; then
  ln -s /content/images.zip /content/bdd100k_images_100k.zip
fi
run setup_$ID python3 -u /content/ypacket/remote.py setup
run train_$ID python3 -u /content/ypacket/remote.py train --name $ID --epochs 100 --imgsz 1280 --batch 16 --seed $SEED
run infer_$ID python3 -u /content/ypacket/remote.py infer --weights /content/runs/$ID/weights/last.pt --out /content/preds/${ID}_1280.npz --imgsz 1280
touch $E/DONE_$ID
