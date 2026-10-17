"""GeoNex C3 synthetic telemetry V2. Not physical observations or landslide ground truth.

Standalone stdlib generator; scenario probabilities randomized once per seeded run.
Outputs complete finite numeric model inputs with explicit provenance/missingness.
"""
from __future__ import annotations
import argparse, csv, gzip, hashlib, json, math, random
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

MODES = ('DEEP_SLEEP','IDLE','RISK','WARNING','EMERGENCY')
INTERVAL = dict(zip(MODES,(900,300,60,15,5)))
DEVICES = ('PIPE_A1','PIPE_B1','PIPE_BK1','HUB_01')
SCENARIOS = ('dry_stable','daily_cycle','intermittent_rain','post_rain_drying','long_rain','cloudburst','rain_pulses','antecedent_wet','wet_no_motion','creep','fast_motion','wet_motion','isolated_vibration','dry_motion','packet_loss','sensor_drift','disagreement','backup_verification')
FIELDS = ('soil_moisture_pct','rainfall_proxy_counts','tilt_deg','vibration_g','fsr_adc','air_temperature_c','humidity_pct')
DEVICE_FIELDS = {'PIPE_A1':('soil_moisture_pct','tilt_deg','vibration_g','fsr_adc','air_temperature_c','humidity_pct'),
                 'PIPE_B1':('soil_moisture_pct','tilt_deg','vibration_g','fsr_adc'),
                 'PIPE_BK1':('soil_moisture_pct','tilt_deg'),
                 'HUB_01':('rainfall_proxy_counts','air_temperature_c','humidity_pct')}


def bounded(x, lo, hi): return round(max(lo,min(hi,x)),4)


def choose_scenario_weights(rng):
    # Deliberately unequal and seed-dependent; no hard-coded equal quotas.
    weights = [rng.gammavariate(1.3,1) for _ in SCENARIOS]
    total=sum(weights)
    return {s: round(w/total,7) for s,w in zip(SCENARIOS,weights)}


def environment_step(rng, kind, k, n, state, params):
    f=k/max(n-1,1)
    cycle=max(0,math.sin(math.pi*(f*params['rain_cycles']+params['phase'])))
    rainfall=0.
    if kind in ('intermittent_rain','rain_pulses','packet_loss','sensor_drift','disagreement','backup_verification'):
        rainfall=params['rain_strength'] * cycle * (rng.random()>.30)
    elif kind in ('long_rain','antecedent_wet','wet_no_motion','wet_motion'):
        rainfall=params['rain_strength']*(.35+.65*cycle)
    elif kind=='cloudburst': rainfall=params['rain_strength']*(.15+2.3*math.exp(-((f-.52)/.13)**2))
    elif kind=='post_rain_drying': rainfall=params['rain_strength']*max(0,1-3*f)
    elif kind in ('fast_motion','creep'): rainfall=params['rain_strength']*.07*rng.random()
    else: rainfall=params['rain_strength']*.02*rng.random()
    rainfall=max(0,rainfall+rng.gauss(0,.3))
    # Simplified water-balance proxy; rates depend on elapsed time, not sample index.
    hours=params['elapsed_seconds']/3600
    state['moisture'] += (rainfall*.20 - (.16+.014*max(state['moisture']-45,0)))*hours + rng.gauss(0,.025)
    state['moisture']=max(12,min(94,state['moisture']))
    drift=0
    if kind in ('creep','wet_motion','dry_motion'): drift=.006 + .015*f
    if kind=='fast_motion': drift=.008 + .12*max(0,f-.40)
    if kind=='wet_no_motion': drift=0
    state['tilt'] = max(0,state['tilt']+drift*hours+rng.gauss(0,.0009))
    temp=26+3.3*math.sin(2*math.pi*(f+params['phase']))+rng.gauss(0,.22)
    humidity=bounded(58+.8*rainfall+(.20*state['moisture'])- .7*(temp-26)+rng.gauss(0,1.5),25,100)
    return {'soil_moisture_pct':bounded(state['moisture'],0,100),
            'rainfall_proxy_counts':bounded(rainfall,0,200),
            'tilt_deg':bounded(state['tilt'],0,35),
            'vibration_g':bounded(.012+(.13 if kind=='isolated_vibration' and .46<f<.49 else 0)+rng.gauss(0,.003),0,2),
            'fsr_adc':bounded(900+state['tilt']*16+rng.gauss(0,9),0,4095),
            'air_temperature_c':bounded(temp,-10,60),'humidity_pct':humidity}


def build(output, seed=20261017, episodes=240, min_packets=30000):
    output=Path(output)
    if output.exists(): raise FileExistsError(f'Refusing to overwrite existing dataset: {output}')
    if episodes<18 or min_packets<1000: raise ValueError('Need >=18 episodes and >=1000 packets')
    rng=random.Random(seed)
    weights=choose_scenario_weights(rng)
    scenario_names=list(weights); scenario_probs=list(weights.values())
    # Guarantee coverage, then randomize rest with deliberately unequal proportions.
    kinds=list(SCENARIOS)+rng.choices(scenario_names,weights=scenario_probs,k=episodes-len(SCENARIOS))
    rng.shuffle(kinds)
    # Make episodes long enough for >target count; stop only at episode boundary.
    steps_per_episode=max(40,math.ceil(min_packets/(episodes*3.25)))
    output.mkdir(parents=True)
    packet_file=output/'telemetry.jsonl.gz'
    manifest_rows=[]; counts=Counter(); modes=Counter(); split_counts=Counter(); corrected=Counter(); total=0
    with gzip.open(packet_file,'wt',encoding='utf-8') as fp:
        for ep,kind in enumerate(kinds):
            erng=random.Random(seed*1000003+ep*7919)
            # Group-level split; all devices/time windows of an episode stay together.
            split=('train' if ep%20<14 else 'validation' if ep%20<17 else 'test')
            start=datetime(2026,1,1,tzinfo=timezone.utc)+timedelta(days=ep*2,hours=erng.randint(0,23))
            state={'moisture':erng.uniform(22,74),'tilt':erng.uniform(.1,1.5)}
            params={'rain_strength':erng.uniform(3,22),'rain_cycles':erng.uniform(.6,4),
                    'phase':erng.random(),'elapsed_seconds':300}
            last={}; last_seen={}; previous_time=None; t=start; current_mode='IDLE'; hold=0
            device_bias={d:erng.uniform(-3,3) for d in DEVICES}
            episode_n=0
            for k in range(steps_per_episode):
                dt=0 if previous_time is None else (t-previous_time).total_seconds()
                params['elapsed_seconds']=dt or 300
                truth=environment_step(erng,kind,k,steps_per_episode,state,params)
                # Controller uses currently available simulated measurements only.
                score=0
                if truth['soil_moisture_pct']>65: score+=1
                if truth['rainfall_proxy_counts']>10: score+=1
                if truth['tilt_deg']>1.0: score+=1
                if truth['tilt_deg']>1.35: score+=2
                requested='EMERGENCY' if score>=4 else 'WARNING' if score>=3 else 'RISK' if score>=2 else 'DEEP_SLEEP'
                # Scheduled low-rate windows, with evidence-based escalation and cooldown.
                scheduled='DEEP_SLEEP' if (k//18)%7==0 else 'IDLE'
                candidate=max((requested,scheduled),key=MODES.index)
                if MODES.index(candidate)>MODES.index(current_mode): current_mode=candidate; hold=8
                elif MODES.index(candidate)<MODES.index(current_mode):
                    if hold>0: hold-=1
                    else: current_mode=MODES[max(MODES.index(current_mode)-1,MODES.index(candidate))];hold=5
                else: hold=max(0,hold-1)
                # Event-driven backup, plus occasional low-rate verification.
                active=['PIPE_A1','PIPE_B1','HUB_01']
                if current_mode in ('WARNING','EMERGENCY') or k%12==0 or kind in ('backup_verification','disagreement'):
                    active.append('PIPE_BK1')
                for device in active:
                    # Packet loss is simulated by absent packets, not fabricated null measurements.
                    if erng.random()<(.11 if kind=='packet_loss' else .006): continue
                    values={}; masks={}; imputed={}; corrected_flags={}; ages={}; methods={}
                    for field in FIELDS:
                        installed=field in DEVICE_FIELDS[device]
                        key=(device,field)
                        raw=truth[field]
                        if field=='soil_moisture_pct': raw+=device_bias[device]+erng.gauss(0,.65)
                        elif field=='tilt_deg': raw+=device_bias[device]*.03+erng.gauss(0,.035)
                        elif field=='rainfall_proxy_counts': raw=max(0,raw+erng.gauss(0,.7))
                        elif field=='fsr_adc': raw+=device_bias[device]*7+erng.gauss(0,12)
                        else: raw+=erng.gauss(0,.2)
                        if kind=='sensor_drift' and device=='PIPE_A1' and field=='soil_moisture_pct': raw+=12*k/steps_per_episode
                        if kind=='disagreement' and device=='PIPE_B1' and field=='soil_moisture_pct': raw-=10*k/steps_per_episode
                        missing=installed and erng.random()<(.085 if kind=='packet_loss' else .012)
                        # Numerical tensor values never contain nulls. Masks/ages disclose absence.
                        observed=installed and not missing
                        if observed:
                            value=bounded(raw,0,4095 if field=='fsr_adc' else 100 if field in ('soil_moisture_pct','humidity_pct') else 200 if field=='rainfall_proxy_counts' else 60 if field=='air_temperature_c' else 35 if field=='tilt_deg' else 2)
                            last[key]=value;last_seen[key]=t
                        else:
                            value=last.get(key,0.0)
                        age=0.0 if observed else (t-last_seen[key]).total_seconds() if key in last_seen else -1.0
                        values[field]=value
                        masks[field]=observed
                        imputed[field]=installed and not observed
                        corrected_flags[field]=False
                        ages[field]=age
                        methods[field]='OBSERVED' if observed else 'LAST_VALID' if key in last else 'NO_OBSERVATION_PLACEHOLDER'
                        if installed and not observed: corrected['imputed']+=1
                    latency=bounded(max(.1,erng.lognormvariate(.4,.65)),0,200)
                    if kind=='packet_loss' and erng.random()<.1: latency+=erng.uniform(20,240)
                    packet={'schema_version':'c3-synthetic-v2','source_origin':'SIMULATED',
                        'scenario_id':f'SIM_EP_{ep:05d}','scenario_family':kind,'split':split,
                        'packet_id':f'SIM_V2_{seed}_{ep:05d}_{device}_{k:05d}',
                        'zone_id':'ZONE_01','device_id':device,'gateway_id':'BLACK_BOX_01',
                        'observed_at':t.isoformat(),'received_at':(t+timedelta(seconds=latency)).isoformat(),
                        'delta_t_seconds':dt,'scheduled_mode':scheduled,'effective_mode':current_mode,
                        'mode_change_reason':'EVIDENCE_ESCALATION' if MODES.index(requested)>MODES.index(scheduled) else 'SCHEDULE_OR_RECOVERY',
                        'features':values,'masks':masks,'imputed_flags':imputed,'corrected_flags':corrected_flags,
                        'ages_seconds':ages,'imputation_methods':methods,
                        'simulated_event_label':None}
                    fp.write(json.dumps(packet,separators=(',',':'),allow_nan=False)+'\n')
                    total+=1;episode_n+=1;modes[current_mode]+=1;split_counts[split]+=1
                previous_time=t
                t+=timedelta(seconds=INTERVAL[current_mode])
            counts[kind]+=episode_n
            manifest_rows.append({'scenario_id':f'SIM_EP_{ep:05d}','scenario_family':kind,'split':split,'packets':episode_n,'start_time':start.isoformat(),'seed':seed*1000003+ep*7919})
    (output/'episodes.json').write_text(json.dumps(manifest_rows,indent=2),encoding='utf-8')
    sha=hashlib.sha256(packet_file.read_bytes()).hexdigest()
    manifest={'dataset_version':'c3-synthetic-v2','source_origin':'SIMULATED',
      'not_field_data':True,'not_landslide_ground_truth':True,
      'training_objective':'UNLABELED_TELEMETRY_PREPARATION; EVENT_LABELS_NOT_DEFINED',
      'seed':seed,'episodes':episodes,'steps_per_episode':steps_per_episode,
      'packets':total,'scenario_family_packet_counts':dict(counts),
      'mode_packet_counts':dict(modes),'split_packet_counts':dict(split_counts),
      'imputed_feature_count':corrected['imputed'],
      'missingness_policy':'Finite numeric placeholder + observed mask + age + imputed flag; no future interpolation',
      'mode_policy':'Synthetic scheduled/evidence controller; not field-validated; no ML forecast feedback',
      'hardware':'Planned simulated Pipe A, Pipe B, Backup Pipe, Sensor Hub; Black Box gateway; power unit not environmental sensor',
      'packet_file':'telemetry.jsonl.gz','packet_sha256':sha,
      'limitations':['Heuristic environmental dynamics, not calibrated geotechnical simulation',
       'Scenario families and noise assumptions may create synthetic artifacts',
       'No verified landslide labels or real-world risk probability',
       'Sensor profile and thresholds are provisional',
       'Training splits are episode-disjoint, not independent simulator-family validation']}
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    return manifest

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output-dir',required=True);p.add_argument('--seed',type=int,default=20261017);p.add_argument('--episodes',type=int,default=240);p.add_argument('--min-packets',type=int,default=30000)
    a=p.parse_args();m=build(a.output_dir,a.seed,a.episodes,a.min_packets)
    print(f"Generated {m['packets']} SIMULATED packets in {a.output_dir}; sha256={m['packet_sha256']}")
