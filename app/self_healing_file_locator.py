"""Locate and modify framework files during self-healing."""

from pathlib import Path
from typing import Optional, Tuple, Dict
import re


def find_test_file_by_error(logs: str, framework_root: Path) -> Optional[Path]:
    """Extract test file path from error logs."""
    match = re.search(r'at ([^\s]+\.spec\.ts):\d+:\d+', logs)
    if match:
        file_path = Path(match.group(1))
        if file_path.exists():
            return file_path
        rel_path = framework_root / file_path.name
        if rel_path.exists():
            return rel_path
    
    match = re.search(r'(tests/[^\s]+\.spec\.ts)', logs)
    if match:
        rel_path = framework_root / match.group(1)
        if rel_path.exists():
            return rel_path
    
    tests_dir = framework_root / "tests"
    if tests_dir.exists():
        test_files = sorted(tests_dir.glob("*.spec.ts"), key=lambda p: p.stat().st_mtime, reverse=True)
        if test_files:
            return test_files[0]
    
    return None


def extract_locator_changes(original_script: str, healed_script: str) -> Dict[str, str]:
    """Extract locator changes by comparing scripts."""
    changes = {}
    
    locator_patterns = [
        r"locator\(['\"]([^'\"]+)['\"]\)",
        r"getByRole\(['\"]([^'\"]+)['\"](?:,\s*\{[^}]+\})?\)",
        r"getByTestId\(['\"]([^'\"]+)['\"]\)",
        r"getByLabel\(['\"]([^'\"]+)['\"]\)",
        r"getByText\(['\"]([^'\"]+)['\"]\)",
        r"getByPlaceholder\(['\"]([^'\"]+)['\"]\)",
    ]
    
    original_locators = set()
    healed_locators = set()
    
    for pattern in locator_patterns:
        original_locators.update(re.findall(pattern, original_script))
        healed_locators.update(re.findall(pattern, healed_script))
    
    removed = original_locators - healed_locators
    added = healed_locators - original_locators
    
    orig_lines = original_script.split('\n')
    heal_lines = healed_script.split('\n')
    
    for old_loc in removed:
        old_line_idx = next((i for i, line in enumerate(orig_lines) if old_loc in line), None)
        if old_line_idx is None:
            continue
        
        for new_loc in added:
            new_line_idx = next((i for i, line in enumerate(heal_lines) if new_loc in line), None)
            if new_line_idx is not None and abs(new_line_idx - old_line_idx) <= 2:
                changes[old_loc] = new_loc
                added.discard(new_loc)
                break
    
    return changes


def update_all_framework_files(
    framework_root: Path,
    failed_locators: list,
    healed_script: str,
    original_script: str = ""
) -> Tuple[int, list]:
    """Update test and locator files with healed content."""
    updated_files = []
    
    locator_changes = extract_locator_changes(original_script, healed_script) if original_script else {}
    
    tests_dir = framework_root / "tests"
    if tests_dir.exists():
        for test_file in tests_dir.glob("*.spec.ts"):
            backup = test_file.with_suffix(test_file.suffix + '.backup')
            backup.write_text(test_file.read_text(encoding='utf-8'), encoding='utf-8')
            test_file.write_text(healed_script, encoding='utf-8')
            updated_files.append(str(test_file))
            break
    
    locators_dir = framework_root / "locators"
    if locators_dir.exists() and locator_changes:
        for locator_file in locators_dir.glob("*.ts"):
            content = locator_file.read_text(encoding='utf-8')
            updated = False
            
            for old_loc, new_loc in locator_changes.items():
                if old_loc in content:
                    content = content.replace(f"'{old_loc}'", f"'{new_loc}'")
                    content = content.replace(f'"{old_loc}"', f'"{new_loc}"')
                    updated = True
            
            if updated:
                backup = locator_file.with_suffix(locator_file.suffix + '.backup')
                backup.write_text(locator_file.read_text(encoding='utf-8'), encoding='utf-8')
                locator_file.write_text(content, encoding='utf-8')
                updated_files.append(str(locator_file))
    
    return len(updated_files), updated_files
