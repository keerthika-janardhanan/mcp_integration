import json
from pathlib import Path

# Read metadata.json
metadata_path = Path("recordings/chines/metadata.json")
with open(metadata_path, 'r', encoding='utf-8') as f:
    content = f.read()
    # Fix incomplete JSON by adding closing braces
    if not content.rstrip().endswith('}'):
        content = content.rstrip().rstrip(',') + '\n    }\n  }\n}'
    metadata = json.loads(content)

# Extract steps and pages
steps_data = []
pages_dict = {}

for idx, step in enumerate(metadata, start=1):
    page_url = step.get('pageUrl', '')
    page_title = step.get('pageTitle', '')
    page_id = step.get('pageId', '')
    
    # Track pages
    if page_id and page_id not in pages_dict:
        pages_dict[page_id] = {
            'pageId': page_id,
            'pageUrl': page_url,
            'pageTitle': page_title,
            'mainHeading': None
        }
    
    # Build step
    element = step.get('element', {})
    selector = element.get('selector', {})
    
    step_data = {
        'step': idx,
        'action': step.get('action', '').capitalize(),
        'navigation': f"{step.get('action', '')} {step.get('visibleText', '')}".strip(),
        'data': '',
        'expected': 'Element responds as expected.',
        'pageUrl': page_url,
        'pageTitle': page_title,
        'pageId': page_id,
        'locators': {
            'playwright': selector.get('playwright', {}).get('byRole', '') or selector.get('playwright', {}).get('byText', '') or selector.get('playwright', {}).get('byLabel', ''),
            'stable': selector.get('css', ''),
            'xpath': selector.get('xpath', ''),
            'xpath_candidates': [selector.get('xpath', '')],
            'raw_xpath': selector.get('xpath', ''),
            'css': selector.get('css', ''),
            'title': '',
            'labels': '',
            'role': '',
            'name': '',
            'tag': '',
            'heading': '',
            'page_heading': ''
        }
    }
    steps_data.append(step_data)

# Build refined JSON
refined = {
    'refinedVersion': '2025.10',
    'flow_name': 'chines',
    'flow_id': 'chines',
    'generated_at': '2026-01-28T11:37:05.040851+00:00',
    'original_url': pages_dict.get('page-1', {}).get('pageUrl', ''),
    'pages': list(pages_dict.values()),
    'elements': [],
    'steps': steps_data
}

# Write refined JSON
output_path = Path('app/generated_flows/chines-chines.refined.json')
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(refined, f, indent=2)

print(f"✓ Generated {output_path}")
print(f"  Pages: {len(pages_dict)}")
print(f"  Steps: {len(steps_data)}")
