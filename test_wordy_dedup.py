from app.recorder.recorder_auto_ingest import auto_refine_and_ingest
import json

with open('recordings/wordy/metadata.json', 'r') as f:
    metadata = json.load(f)

print('Testing improved deduplication...')
result = auto_refine_and_ingest('recordings/wordy', metadata, ingest=False)
print('✅ Success!')
print('Refined file:', result.get('refined_path'))

with open(result.get('refined_path'), 'r') as f:
    refined = json.load(f)

step_count = len(refined['steps'])
print(f'\n📊 Steps reduced from 11 to {step_count}\n')
print('Actions:')
for i, s in enumerate(refined['steps']):
    text = s.get('visibleText', '')[:30] if s.get('visibleText') else 'form field'
    print(f"{i+1}. {s['action']:8s} - {text}")
