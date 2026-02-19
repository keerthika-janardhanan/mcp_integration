"""Enhanced executor with automatic self-healing on XPath/locator failures.

Uses VS Code Copilot API for healing and generated flows from app/generated_flow.
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def ask_copilot_to_self_heal(
    failed_script: str,
    logs: str,
    ui_crawl: str
) -> str:
    """Use VS Code Copilot API to heal failed script.
    
    This function calls the VS Code Copilot API (not Azure OpenAI) to analyze
    the failed script and generate better locators using Microsoft Docs MCP
    for official Playwright patterns and generated flows from app/generated_flow.
    
    Args:
        failed_script: The test script with failed locators
        logs: Error logs from test execution
        ui_crawl: JSON string of UI crawl data from Playwright MCP
        
    Returns:
        Healed script with improved locators
    """
    # This will be implemented by calling VS Code Copilot API
    # For now, falls back to llm_client if available
    try:
        from .core.llm_client import ask_llm_to_self_heal
        logger.info("[SelfHealing] Using llm_client.ask_llm_to_self_heal() as Copilot bridge")
        return ask_llm_to_self_heal(failed_script, logs, ui_crawl)
    except ImportError:
        logger.warning("[SelfHealing] Copilot API not configured, returning original script")
        return failed_script


def extract_failed_locators_from_logs(logs: str) -> List[Dict[str, str]]:
    """Extract failed locators from Playwright error logs.
    
    Args:
        logs: Playwright execution logs
        
    Returns:
        List of failed locators with error context
    """
    failed_locators = []
    
    # Common Playwright error patterns (more comprehensive)
    patterns = [
        # XPath in locator() - e.g., locator('xpath=//button[@id="old-btn"]')
        (r"locator\(['\"]xpath=([^'\"]+)['\"]\)", "xpath"),
        # CSS in locator() - e.g., locator('css=#element')
        (r"locator\(['\"]css=([^'\"]+)['\"]\)", "css"),
        # Direct locator() - e.g., locator('#element')
        (r"locator\(['\"]([^'\"]+)['\"]\)(?!\.)", "selector"),
        # getByRole - e.g., getByRole('button', { name: 'Submit' })
        (r"getByRole\(['\"]([^'\"]+)['\"](?:,\s*\{\s*name:\s*['\"]([^'\"]+)['\"])?\)", "role"),
        # getByLabel
        (r"getByLabel\(['\"]([^'\"]+)['\"]\)", "label"),
        # getByText
        (r"getByText\(['\"]([^'\"]+)['\"]\)", "text"),
        # getByTestId
        (r"getByTestId\(['\"]([^'\"]+)['\"]\)", "testid"),
        # getByPlaceholder
        (r"getByPlaceholder\(['\"]([^'\"]+)['\"]\)", "placeholder"),
    ]
    
    for pattern, loc_type in patterns:
        matches = re.finditer(pattern, logs, re.IGNORECASE | re.DOTALL)
        for match in matches:
            # Check if this match is near a timeout/error
            error_context_start = max(0, match.start() - 200)
            error_context_end = min(len(logs), match.end() + 200)
            error_context = logs[error_context_start:error_context_end]
            
            # Only include if there's an error nearby
            if any(err in error_context.lower() for err in ['timeout', 'error', 'not found', 'failed']):
                locator = match.group(1)
                
                # For getByRole with name, combine them
                if loc_type == "role" and match.lastindex >= 2 and match.group(2):
                    locator = f"{locator} with name '{match.group(2)}'"
                
                # Get surrounding context (100 chars before and after)
                context_start = max(0, match.start() - 100)
                context_end = min(len(logs), match.end() + 100)
                context = logs[context_start:context_end]
                
                failed_locators.append({
                    "locator": locator,
                    "context": context.strip(),
                    "type": loc_type
                })
    
    return failed_locators


def capture_ui_crawl_on_failure(logs: str) -> Dict[str, any]:
    """Simulate UI crawl data capture (in real implementation, would use Playwright MCP).
    
    Args:
        logs: Playwright execution logs with page info
        
    Returns:
        UI crawl data structure
    """
    # In production, this would:
    # 1. Use Playwright MCP browser_snapshot to capture current page
    # 2. Use browser_evaluate to get element attributes
    # 3. Build comprehensive UI crawl data
    
    # For now, return placeholder structure
    return {
        "page_title": "Captured Page",
        "url": "https://captured-url.com",
        "elements": [
            {
                "tag": "button",
                "attributes": {
                    "id": "submit-btn",
                    "class": "btn btn-primary",
                    "role": "button",
                    "aria-label": "Submit form"
                },
                "text": "Submit",
                "xpath": "//button[@id='submit-btn']",
                "css": "button#submit-btn.btn.btn-primary"
            }
        ],
        "note": "UI crawl data would be captured here using Playwright MCP browser_snapshot"
    }


def run_trial_with_self_healing(
    script_content: str,
    framework_root: Path,
    max_retries: int = 2,
    headed: bool = True,
    env_overrides: Optional[Dict[str, str]] = None,
    auto_update_files: bool = True
) -> Tuple[bool, str, List[Dict[str, str]]]:
    """Run trial with automatic self-healing on locator failures.
    
    Args:
        script_content: Test script content
        framework_root: Framework root path
        max_retries: Maximum self-healing retry attempts
        headed: Run in headed mode
        env_overrides: Environment variable overrides
        auto_update_files: Automatically update framework files with healed locators
        
    Returns:
        Tuple of (success, logs, healing_attempts)
    """
    from .executor import run_trial_in_framework
    
    print("\n" + "="*60)
    print("SELF-HEALING TRIAL EXECUTION")
    print("="*60)
    print(f"Max retries: {max_retries}")
    print(f"Headed mode: {headed}")
    print(f"Framework: {framework_root}")
    print(f"Self-healing timeout mode: ENABLED (faster failures for quick retries)")
    print("="*60 + "\n")
    
    healing_attempts = []
    current_script = script_content
    
    # Set self-healing mode for faster timeouts
    if env_overrides is None:
        env_overrides = {}
    env_overrides['SELF_HEALING_MODE'] = 'true'
    
    for attempt in range(max_retries + 1):
        logger.info(f"[SelfHealing] Trial attempt {attempt + 1}/{max_retries + 1}")
        print(f"[SelfHealing] ===== TRIAL ATTEMPT {attempt + 1}/{max_retries + 1} =====")
        
        # Run trial
        success, logs = run_trial_in_framework(
            current_script,
            framework_root,
            headed=headed,
            env_overrides=env_overrides
        )
        
        if success:
            logger.info(f"[SelfHealing] ✅ Test passed on attempt {attempt + 1}")
            print(f"[SelfHealing] ✅ Test PASSED on attempt {attempt + 1}")
            return success, logs, healing_attempts
        
        # Test failed - check if it's a locator issue
        print(f"[SelfHealing] ❌ Test FAILED on attempt {attempt + 1}")
        print(f"[SelfHealing] Analyzing failure logs for locator errors...")
        failed_locators = extract_failed_locators_from_logs(logs)
        print(f"[SelfHealing] Found {len(failed_locators)} failed locators: {failed_locators}")
        
        if not failed_locators:
            logger.warning("[SelfHealing] Test failed but no locator errors detected")
            print("[SelfHealing] ⚠️ Test failed but NO locator errors found - cannot self-heal")
            return success, logs, healing_attempts
        
        if attempt >= max_retries:
            logger.warning(f"[SelfHealing] Max retries ({max_retries}) reached")
            print(f"[SelfHealing] ⚠️ Max retries ({max_retries}) reached - giving up")
            return success, logs, healing_attempts
        
        # Attempt self-healing
        logger.info(f"[SelfHealing] 🔧 Attempting self-healing (found {len(failed_locators)} failed locators)")
        print(f"[SelfHealing] 🔧 Starting self-healing for {len(failed_locators)} failed locators...")
        print(f"[SelfHealing] Failed locators: {', '.join(failed_locators)}")
        
        # Capture UI state (in production, use Playwright MCP)
        ui_crawl = capture_ui_crawl_on_failure(logs)
        
        try:
            # Call self-healing function using VS Code Copilot API
            healed_script = ask_copilot_to_self_heal(
                failed_script=current_script,
                logs=logs,
                ui_crawl=json.dumps(ui_crawl, indent=2)
            )
            
            if not healed_script or healed_script == current_script:
                logger.warning("[SelfHealing] Self-healing returned no changes")
                return success, logs, healing_attempts
            
            # Auto-update framework files if enabled
            if auto_update_files:
                from .self_healing_file_locator import update_all_framework_files
                count, files = update_all_framework_files(
                    framework_root, 
                    failed_locators, 
                    healed_script,
                    current_script  # Pass original for comparison
                )
                logger.info(f"[SelfHealing] 📝 Updated {count} files: {files}")
                print(f"[SelfHealing] ✅ Updated {count} framework files")
            
            # Store healing attempt
            healing_attempts.append({
                "attempt": attempt + 1,
                "failed_locators": failed_locators,
                "healed": True,
                "changes": "Applied self-healing fixes"
            })
            
            current_script = healed_script
            logger.info(f"[SelfHealing] ✅ Applied self-healing fixes, retrying...")
            
        except Exception as e:
            logger.error(f"[SelfHealing] Self-healing failed: {e}")
            healing_attempts.append({
                "attempt": attempt + 1,
                "failed_locators": failed_locators,
                "healed": False,
                "error": str(e)
            })
            return success, logs, healing_attempts
    
    return success, logs, healing_attempts


def save_healed_script(
    script_content: str,
    framework_root: Path,
    test_name: str
) -> Path:
    """Save healed script to framework for future use.
    
    Args:
        script_content: Healed script content
        framework_root: Framework root path
        test_name: Name of the test
        
    Returns:
        Path to saved script
    """
    from .core.mcp_client import get_filesystem_mcp
    
    test_dir = framework_root / "tests"
    test_dir.mkdir(parents=True, exist_ok=True)
    
    # Sanitize test name for filename
    safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', test_name)
    test_file = test_dir / f"{safe_name}.spec.ts"
    
    # Use Filesystem MCP for safe write with backup
    fs_mcp = get_filesystem_mcp()
    success = fs_mcp.safe_write_file(test_file, script_content, backup=True)
    
    if success:
        logger.info(f"[SelfHealing] 💾 Saved healed script to: {test_file}")
    else:
        logger.error(f"[SelfHealing] Failed to save healed script to: {test_file}")
    
    return test_file


# Example usage function
def run_trial_with_smart_healing_example():
    """Example of how to use the self-healing trial runner."""
    
    script = """
    import { test, expect } from '@playwright/test';
    
    test('example test', async ({ page }) => {
      await page.goto('https://example.com');
      
      // This XPath might be incorrect
      await page.locator('xpath=//button[@id="old-submit-id"]').click();
      
      // Or this CSS selector might fail
      await page.locator('#non-existent-element').fill('test');
      
      await expect(page.locator('text=Success')).toBeVisible();
    });
    """
    
    framework_root = Path("./framework_repos/my-framework")
    
    # Run with automatic self-healing
    success, logs, healing_attempts = run_trial_with_self_healing(
        script_content=script,
        framework_root=framework_root,
        max_retries=2,
        headed=True
    )
    
    print(f"\nTest Result: {'PASSED ✅' if success else 'FAILED ❌'}")
    print(f"Healing Attempts: {len(healing_attempts)}")
    
    for attempt in healing_attempts:
        print(f"\nAttempt {attempt['attempt']}:")
        print(f"  Failed Locators: {len(attempt['failed_locators'])}")
        print(f"  Healed: {attempt['healed']}")
        if attempt['healed']:
            print(f"  Changes: {attempt['changes']}")
    
    if success and healing_attempts:
        # Save the healed script
        save_healed_script(script, framework_root, "healed_example")
    
    return success, logs, healing_attempts
