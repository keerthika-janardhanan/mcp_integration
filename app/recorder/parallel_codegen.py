"""Parallel Playwright Codegen Recorder.

Runs Playwright's native codegen in headless mode alongside our recorder
to capture ALL actions, then merges missing actions at the end.
"""
from __future__ import annotations

import json
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


class ParallelCodegenRecorder:
    """Run Playwright codegen in parallel to capture all actions."""
    
    def __init__(self, session_dir: Path, url: str):
        self.session_dir = session_dir
        self.url = url
        self.codegen_file = session_dir / "codegen_actions.json"
        self.process: Optional[subprocess.Popen] = None
        self.actions: List[Dict[str, Any]] = []
        
    def start(self) -> None:
        """Start Playwright codegen in background."""
        # Playwright codegen with JSON output
        cmd = [
            "playwright",
            "codegen",
            self.url,
            "--target", "python",
            "--output", str(self.codegen_file),
            "--browser", "chromium"
        ]
        
        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        print(f"[codegen] Started parallel codegen recorder (PID: {self.process.pid})")
    
    def stop(self) -> None:
        """Stop codegen and parse captured actions."""
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            
            print(f"[codegen] Stopped codegen recorder")
            
            # Parse codegen output
            if self.codegen_file.exists():
                self._parse_codegen_output()
    
    def _parse_codegen_output(self) -> None:
        """Parse Playwright codegen output to extract actions."""
        try:
            content = self.codegen_file.read_text(encoding='utf-8')
            
            # Parse Python code to extract actions
            # Playwright codegen generates code like:
            # page.goto("url")
            # page.get_by_role("button").click()
            # page.get_by_label("Email").fill("text")
            
            for line in content.split('\n'):
                line = line.strip()
                
                # Extract click actions
                if '.click()' in line:
                    selector = self._extract_selector(line)
                    if selector:
                        self.actions.append({
                            'action': 'click',
                            'selector': selector,
                            'source': 'codegen'
                        })
                
                # Extract fill actions
                elif '.fill(' in line:
                    selector = self._extract_selector(line)
                    if selector:
                        self.actions.append({
                            'action': 'fill',
                            'selector': selector,
                            'source': 'codegen'
                        })
                
                # Extract check actions
                elif '.check()' in line:
                    selector = self._extract_selector(line)
                    if selector:
                        self.actions.append({
                            'action': 'check',
                            'selector': selector,
                            'source': 'codegen'
                        })
                
                # Extract select actions
                elif '.select_option(' in line:
                    selector = self._extract_selector(line)
                    if selector:
                        self.actions.append({
                            'action': 'select',
                            'selector': selector,
                            'source': 'codegen'
                        })
            
            print(f"[codegen] Parsed {len(self.actions)} actions from codegen")
            
        except Exception as e:
            print(f"[codegen] Error parsing codegen output: {e}")
    
    def _extract_selector(self, line: str) -> Optional[str]:
        """Extract selector from codegen line."""
        # Examples:
        # page.get_by_role("button", name="Submit").click()
        # page.get_by_label("Email").fill("text")
        # page.locator("#id").click()
        
        if 'get_by_role(' in line:
            # Extract role and name
            import re
            match = re.search(r'get_by_role\("([^"]+)"(?:,\s*name="([^"]+)")?\)', line)
            if match:
                role = match.group(1)
                name = match.group(2) if match.group(2) else None
                return f"getByRole('{role}'{f', name: {name}' if name else ''})"
        
        elif 'get_by_label(' in line:
            import re
            match = re.search(r'get_by_label\("([^"]+)"\)', line)
            if match:
                return f"getByLabel('{match.group(1)}')"
        
        elif 'get_by_placeholder(' in line:
            import re
            match = re.search(r'get_by_placeholder\("([^"]+)"\)', line)
            if match:
                return f"getByPlaceholder('{match.group(1)}')"
        
        elif 'locator(' in line:
            import re
            match = re.search(r'locator\("([^"]+)"\)', line)
            if match:
                return match.group(1)
        
        return None
    
    def get_actions(self) -> List[Dict[str, Any]]:
        """Get captured actions."""
        return self.actions


def merge_actions(
    recorded_actions: List[Dict[str, Any]],
    codegen_actions: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Merge codegen actions into recorded actions, adding missing ones."""
    
    # Build set of recorded action signatures
    recorded_sigs = set()
    for action in recorded_actions:
        sig = _action_signature(action)
        if sig:
            recorded_sigs.add(sig)
    
    # Find missing actions
    missing = []
    for action in codegen_actions:
        sig = _action_signature(action)
        if sig and sig not in recorded_sigs:
            missing.append(action)
    
    print(f"[merge] Found {len(missing)} missing actions from codegen")
    
    # Append missing actions
    merged = recorded_actions.copy()
    for action in missing:
        merged.append({
            **action,
            'addedFromCodegen': True,
            'timestamp': None
        })
    
    return merged


def _action_signature(action: Dict[str, Any]) -> Optional[str]:
    """Generate signature for action matching."""
    action_type = action.get('action', '')
    
    # Try multiple selector strategies
    selector = None
    
    # From codegen
    if 'selector' in action:
        selector = action['selector']
    
    # From recorded metadata
    elif 'element' in action:
        element = action['element']
        if isinstance(element, dict):
            sel_obj = element.get('selector', {})
            if isinstance(sel_obj, dict):
                # Prefer playwright selectors
                pw = sel_obj.get('playwright', {})
                if isinstance(pw, dict):
                    selector = pw.get('byRole') or pw.get('byLabel') or pw.get('byPlaceholder')
                
                # Fallback to CSS/XPath
                if not selector:
                    selector = sel_obj.get('css') or sel_obj.get('xpath')
    
    if not selector:
        return None
    
    return f"{action_type}:{selector}"


# Integration with recorder
def run_with_parallel_codegen(
    session_dir: Path,
    url: str,
    recorder_func: callable
) -> Path:
    """Run recorder with parallel codegen, merge at end."""
    
    # Start codegen
    codegen = ParallelCodegenRecorder(session_dir, url)
    codegen.start()
    
    # Give codegen time to start
    time.sleep(2)
    
    try:
        # Run main recorder
        metadata_path = recorder_func()
        
        return metadata_path
        
    finally:
        # Stop codegen
        codegen.stop()
        
        # Merge actions
        metadata_path = session_dir / "metadata.json"
        if metadata_path.exists():
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            recorded_actions = metadata.get('actions', [])
            codegen_actions = codegen.get_actions()
            
            merged_actions = merge_actions(recorded_actions, codegen_actions)
            
            # Update metadata
            metadata['actions'] = merged_actions
            metadata['codegenMerged'] = True
            metadata['codegenActionsCount'] = len(codegen_actions)
            metadata['missingActionsAdded'] = len(merged_actions) - len(recorded_actions)
            
            # Save merged metadata
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)
            
            print(f"[merge] Added {metadata['missingActionsAdded']} missing actions")
            print(f"[merge] Total actions: {len(merged_actions)}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python -m app.recorder.parallel_codegen <session_dir> <url>")
        sys.exit(1)
    
    session_dir = Path(sys.argv[1])
    url = sys.argv[2]
    
    codegen = ParallelCodegenRecorder(session_dir, url)
    codegen.start()
    
    print("Press Ctrl+C to stop...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    
    codegen.stop()
    
    print(f"\nCaptured {len(codegen.get_actions())} actions")
    for action in codegen.get_actions():
        print(f"  - {action['action']}: {action['selector']}")
