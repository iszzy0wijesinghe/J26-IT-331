"""Read-only, event-derived training telemetry; no synthetic progress values."""
from __future__ import annotations

import re

from fastapi import APIRouter, HTTPException, Query

from apps.c3_workbench.training_queue import get_training_job

router = APIRouter(prefix='/training', tags=['C3 Training Telemetry'])
STAGES = ['TRAINING_M1', 'TRAINING_M2'] + [f'TRAINING_M3_{h}MIN' for h in (15,30,60)] + [f'TRAINING_M4_{a}_{h}MIN' for a in 'ABC' for h in (15,30,60)]
EPOCH_RE = re.compile(r'(?i)\bepoch\s*[:=]?\s*(\d+)(?:\s*(?:/|of)\s*(\d+))?')
METRIC_RE = re.compile(r'(?i)\b(train(?:ing)?[_ -]?(?:loss|mae|rmse)|val(?:idation)?[_ -]?(?:loss|mae|rmse))\s*[:=]\s*(-?\d+(?:\.\d+)?(?:e[+-]?\d+)?)')

@router.get('/jobs/{job_id}/telemetry')
def training_telemetry(job_id: str, limit: int = Query(250, ge=10, le=2000)):
    job = get_training_job(job_id)
    if job is None:
        raise HTTPException(404, 'Training job not found.')
    events = job.get('events', [])
    completed = set()
    started = set()
    points = []
    current_epoch = None
    max_epochs = None
    for event in events:
        stage = str(event.get('stage') or '')
        message = str(event.get('message') or '')
        if stage in STAGES:
            if 'Starting task' in message:
                started.add(stage)
            if 'completed' in message.lower() or 'finished' in message.lower():
                completed.add(stage)
            epoch_match = EPOCH_RE.search(message)
            metrics = {k.lower().replace(' ', '_').replace('-', '_'): float(v) for k,v in METRIC_RE.findall(message)}
            if epoch_match:
                current_epoch = int(epoch_match.group(1))
                max_epochs = int(epoch_match.group(2)) if epoch_match.group(2) else max_epochs
            if epoch_match or metrics:
                points.append({'stage': stage, 'timestamp': event.get('timestamp'), 'epoch': int(epoch_match.group(1)) if epoch_match else None, 'metrics': metrics})
    status = str(job.get('status') or '')
    if status in ('EVALUATING','COMPLETED'):
        completed.update(STAGES)
    active_stage = str(job.get('current_stage') or '')
    if active_stage not in STAGES:
        current_epoch, max_epochs = None, None
    return {
        'job_id': job_id, 'status': status, 'current_stage': active_stage,
        'completed_tasks': len(completed), 'total_tasks': len(STAGES),
        'progress_percent': round(len(completed) / len(STAGES) * 100, 1),
        'progress_basis': 'completed training commands; epoch work is excluded',
        'current_epoch': current_epoch, 'max_epochs': max_epochs,
        'events': events[-limit:], 'metric_points': points[-limit:],
        'started_at': job.get('started_at'), 'completed_at': job.get('completed_at'),
        'error_message': job.get('error_message'),
    }
