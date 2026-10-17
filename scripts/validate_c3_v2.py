"""Validate exported C3 V2 dataset integrity and input quality."""
import argparse, gzip, hashlib, json, math
from collections import Counter
from pathlib import Path

def validate(folder):
    root=Path(folder)
    manifest=json.loads((root/'manifest.json').read_text(encoding='utf-8'))
    packet_path=root/manifest['packet_file']
    assert hashlib.sha256(packet_path.read_bytes()).hexdigest()==manifest['packet_sha256']
    counts=Counter(); episodes={}; packet_ids=set(); modes=set()
    with gzip.open(packet_path,'rt',encoding='utf-8') as f:
        for line in f:
            p=json.loads(line)
            assert p['source_origin']=='SIMULATED'
            assert p['packet_id'] not in packet_ids
            packet_ids.add(p['packet_id'])
            assert p['scenario_id'] not in episodes or episodes[p['scenario_id']]==p['split']
            episodes[p['scenario_id']]=p['split']
            assert set(p['features'])==set(p['masks'])==set(p['imputed_flags'])==set(p['ages_seconds'])
            assert all(isinstance(v,(int,float)) and math.isfinite(v) for v in p['features'].values())
            assert all(isinstance(v,bool) for v in p['masks'].values())
            assert p['simulated_event_label'] is None
            counts[p['split']]+=1; modes.add(p['effective_mode'])
    assert sum(counts.values())==manifest['packets']
    assert len(episodes)==manifest['episodes']
    assert modes=={'DEEP_SLEEP','IDLE','RISK','WARNING','EMERGENCY'}
    assert manifest['packets']>=30000
    return dict(counts)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--dataset-dir',required=True)
    args=p.parse_args();print('PASS:',validate(args.dataset_dir))
