from pathlib import Path
H=Path(__file__).resolve().parent
for n in ['TRAINING_CONFIG.json','TRAINING_FAILURE.json','TRAINING_GUARD.json']:
 p=H/'objects_v2'/n;p.rename(p.with_name(p.stem+'_SANDBOX'+p.suffix))
p=H/'train_objects.py';p.write_text(p.read_text(encoding='utf-8').replace('published_chair_pilot','published_chair_pilot_final'),encoding='utf-8')
