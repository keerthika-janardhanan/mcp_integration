"""Use Playwright's official codegen for reliable recording."""

import subprocess
import json
import re
from pathlib import Path
from datetime import datetime


def record_with_codegen(url: str, output_dir: Path, session_name: str, timeout: int = 600):
    """Record using Playwright codegen and convert to metadata format."""
    
    output_dir.mkdir(parents=True, exist_ok=True)
    session_dir = output_dir / session_name
    session_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate code file
    code_file = session_dir / 'recorded_script.py'
    
    print(f"[Codegen] Starting Playwright codegen...")
    print(f"[Codegen] Recording to: {code_file}")
    print(f"[Codegen] Close the browser when done\n")
    
    # Run playwright codegen
    cmd = [
        'playwright',
        'codegen',
        '--target', 'python',
        '--output', str(code_file),
        url
    ]
    
    try:
        subprocess.run(cmd, timeout=timeout)
    except subprocess.TimeoutExpired:
        print(f"[Codegen] Timeout reached ({timeout}s)")
    except KeyboardInterrupt:
        print("\n[Codegen] Stopped by user")
    
    # Parse generated code to metadata
    if not code_file.exists():
        print("[Codegen] No code generated")
        return None
    
    code = code_file.read_text(encoding='utf-8')
    actions = parse_playwright_code(code)
    
    # Create metadata
    metadata = {
        'metadataVersion': '2025.codegen',
        'flowId': session_name,
        'startTime': datetime.now().isoformat(),
        'startUrl': url,
        'browser': 'chromium',
        'actions': actions,
        'pages': {'page-1': {'pageId': 'page-1', 'url': url}},
        'endTime': datetime.now().isoformat(),
        'totalActions': len(actions),
        'totalPages': 1
    }
    
    metadata_path = session_dir / 'metadata.json'
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    
    print(f"\n[Codegen] Captured {len(actions)} actions")
    print(f"[Codegen] Metadata saved to: {metadata_path}")
    
    return metadata_path


def parse_playwright_code(code: str):
    """Parse Playwright Python code to extract actions."""
    actions = []
    timestamp = int(datetime.now().timestamp() * 1000)
    
    # Extract page.goto
    goto_match = re.search(r'page\.goto\(["\']([^"\']+)["\']\)', code)
    if goto_match:
        actions.append({
            'action': 'navigate',
            'timestamp': timestamp,
            'pageUrl': goto_match.group(1),
            'pageTitle': '',
            'element': {},
            'pageId': 'page-1'
        })
        timestamp += 100
    
    # Extract clicks
    for match in re.finditer(r'page\.(get_by_\w+|locator)\(([^)]+)\)\.click\(\)', code):
        selector = match.group(0).replace('.click()', '')
        actions.append({
            'action': 'click',
            'timestamp': timestamp,
            'pageUrl': '',
            'pageTitle': '',
            'element': {'selector': {'playwright': selector}},
            'pageId': 'page-1'
        })
        timestamp += 100
    
    # Extract fills
    for match in re.finditer(r'page\.(get_by_\w+|locator)\(([^)]+)\)\.fill\(["\']([^"\']*)["\']', code):
        selector = match.group(0).split('.fill')[0]
        value = match.group(3)
        actions.append({
            'action': 'fill',
            'timestamp': timestamp,
            'pageUrl': '',
            'pageTitle': '',
            'element': {'selector': {'playwright': selector}, 'value': value},
            'pageId': 'page-1'
        })
        timestamp += 100
    
    # Extract press
    for match in re.finditer(r'page\.(get_by_\w+|locator)\(([^)]+)\)\.press\(["\']([^"\']+)["\']', code):
        selector = match.group(0).split('.press')[0]
        key = match.group(3)
        actions.append({
            'action': 'press',
            'timestamp': timestamp,
            'pageUrl': '',
            'pageTitle': '',
            'element': {'selector': {'playwright': selector}, 'key': key},
            'pageId': 'page-1'
        })
        timestamp += 100
    
    return actions


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', required=True)
    parser.add_argument('--output-dir', default='recordings')
    parser.add_argument('--session-name', default=None)
    parser.add_argument('--timeout', type=int, default=600)
    args = parser.parse_args()
    
    session_name = args.session_name or datetime.now().strftime("%Y%m%d_%H%M%S")
    record_with_codegen(args.url, Path(args.output_dir), session_name, args.timeout)
