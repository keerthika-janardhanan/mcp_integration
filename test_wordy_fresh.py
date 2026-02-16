import importlib
import sys

# Force reload
if 'app.recorder.recorder_auto_ingest' in sys.modules:
    del sys.modules['app.recorder.recorder_auto_ingest']

from app.recorder.recorder_auto_ingest import auto_refine_and_ingest
import json

with open('recordings/wordy/metadata.json', 'r') as f:
    metadata = json.load(f)

print('Testing improved span-inside-button detection...')
result = auto_refine_and_ingest('recordings/wordy', metadata, ingest=False)
print('✅ Success!')
print('Refined file:', result.get('refined_path'))

with open(result.get('refined_path'), 'r') as f:
    refined = json.load(f)

step_count = len(refined['steps'])
print(f'\n📊 Steps: 11 → {step_count} (expected: 5-6)\n')
print('Actions:')
for i, s in enumerate(refined['steps']):
    text = s.get('visibleText', '')[:30] if s.get('visibleText') else 'form field'
    testid = s.get('element', {}).get('html', '')
    has_id = 'data-testid' in testid or 'aria-label' in testid or 'id=' in testid
    id_marker = '✓' if has_id else '✗'
    print(f"{i+1}. {id_marker} {s['action']:8s} - {text}")
