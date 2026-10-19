"""Run from GeoNex repository root after copying patch files."""
from pathlib import Path

p = Path('apps/c3_workbench/api.py')
s = p.read_text()
imp = 'from apps.c3_workbench.training_monitor_routes import router as training_monitor_router\n'
if imp not in s:
    anchor = 'from apps.c3_workbench.training_routes import ('
    if anchor not in s:
        raise SystemExit('Could not find training_routes import in api.py; register training_monitor_router manually.')
    s = s.replace(anchor, imp + anchor, 1)
if 'app.include_router(training_monitor_router)' not in s:
    anchor = 'app.include_router(training_router)'
    if anchor not in s:
        raise SystemExit('Could not find training router registration; register monitor router manually.')
    s = s.replace(anchor, anchor + '\napp.include_router(training_monitor_router)', 1)
p.write_text(s)
print('Registered C3 training telemetry router in api.py')
