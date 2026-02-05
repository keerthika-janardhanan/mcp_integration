"""Self-healing executor with Playwright MCP integration for real-time page capture.

Uses VS Code Copilot API for healing and generated flows from app/generated_flow.
"""

from __future__ import annotations

import json
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .self_healing_executor import extract_failed_locators_from_logs, ask_copilot_to_self_heal
from .recorder.mcp_integration import PlaywrightMCPRecorder

logger = logging.getLogger(__name__)


class SelfHealingExecutor:
    """Executor that captures page state on failure and self-heals locators."""
    
    def __init__(self, framework_root: Path):
        self.framework_root = framework_root
        self.mcp_recorder = PlaywrightMCPRecorder()
        
    def capture_page_state_on_failure(self, test_url: str) -> Dict[str, any]:
        """Capture real page state using Playwright MCP when test fails.
        
        Args:
            test_url: URL where test failed
            
        Returns:
            Complete UI crawl data with all elements
        """
        try:
            # Use Playwright MCP to open page and capture state
            logger.info(f"[SelfHealing] 📸 Capturing page state at: {test_url}")
            
            # Step 1: Open browser with Playwright MCP
            subprocess.run([
                "npx", "@modelcontextprotocol/server-playwright",
                "--action", "browser_open",
                "--url", test_url,
                "--headed", "false"
            ], check=True, capture_output=True, text=True)
            
            # Step 2: Capture accessibility snapshot (better than screenshot)
            result = subprocess.run([
                "npx", "@modelcontextprotocol/server-playwright",
                "--action", "browser_snapshot"
            ], check=True, capture_output=True, text=True)
            
            page_snapshot = json.loads(result.stdout)
            
            # Step 3: Capture console messages for debugging
            console_result = subprocess.run([
                "npx", "@modelcontextprotocol/server-playwright",
                "--action", "browser_console_messages"
            ], check=True, capture_output=True, text=True)
            
            console_messages = json.loads(console_result.stdout)
            
            # Step 4: Capture network requests
            network_result = subprocess.run([
                "npx", "@modelcontextprotocol/server-playwright",
                "--action", "browser_network_requests"
            ], check=True, capture_output=True, text=True)
            
            network_requests = json.loads(network_result.stdout)
            
            # Build comprehensive UI crawl data
            ui_crawl = {
                "url": test_url,
                "snapshot": page_snapshot,
                "console_messages": console_messages,
                "network_requests": network_requests,
                "captured_at": "failure_point",
                "elements": self._parse_elements_from_snapshot(page_snapshot)
            }
            
            logger.info(f"[SelfHealing] ✅ Captured {len(ui_crawl['elements'])} elements from page")
            return ui_crawl
            
        except subprocess.CalledProcessError as e:
            logger.error(f"[SelfHealing] Failed to capture page state: {e}")
            logger.error(f"[SelfHealing] stderr: {e.stderr}")
            return {"error": str(e), "elements": []}
        except Exception as e:
            logger.error(f"[SelfHealing] Unexpected error capturing page state: {e}")
            return {"error": str(e), "elements": []}
    
    def _parse_elements_from_snapshot(self, snapshot: Dict) -> List[Dict]:
        """Parse elements from accessibility snapshot.
        
        Args:
            snapshot: Playwright accessibility snapshot
            
        Returns:
            List of element dictionaries with locator info
        """
        elements = []
        
        def traverse_node(node: Dict, xpath_prefix: str = ""):
            """Recursively traverse accessibility tree."""
            if not node:
                return
            
            # Build element data
            element = {
                "role": node.get("role", ""),
                "name": node.get("name", ""),
                "value": node.get("value", ""),
                "attributes": {},
                "xpath": xpath_prefix,
            }
            
            # Add useful attributes
            if "attributes" in node:
                element["attributes"] = node["attributes"]
            
            # Generate multiple locator strategies
            if element["role"]:
                element["locators"] = self._generate_locator_strategies(element)
            
            elements.append(element)
            
            # Traverse children
            if "children" in node:
                for i, child in enumerate(node["children"]):
                    child_xpath = f"{xpath_prefix}/{child.get('role', '*')}[{i+1}]"
                    traverse_node(child, child_xpath)
        
        # Start traversal from root
        if snapshot and "children" in snapshot:
            for child in snapshot["children"]:
                traverse_node(child, "/")
        
        return elements
    
    def _generate_locator_strategies(self, element: Dict) -> Dict[str, str]:
        """Generate multiple locator strategies for an element.
        
        Args:
            element: Element dictionary
            
        Returns:
            Dictionary of locator strategies
        """
        locators = {}
        
        # Role-based locator (preferred)
        if element.get("role") and element.get("name"):
            locators["role"] = f"page.getByRole('{element['role']}', {{ name: '{element['name']}' }})"
        
        # Label-based locator
        if element.get("name"):
            locators["label"] = f"page.getByLabel('{element['name']}')"
        
        # Text-based locator
        if element.get("name"):
            locators["text"] = f"page.getByText('{element['name']}')"
        
        # TestId-based locator (if present)
        if "data-testid" in element.get("attributes", {}):
            test_id = element["attributes"]["data-testid"]
            locators["testid"] = f"page.getByTestId('{test_id}')"
        
        # XPath (fallback)
        if element.get("xpath"):
            locators["xpath"] = f"page.locator('xpath={element['xpath']}')"
        
        return locators
    
    def run_trial_with_real_time_healing(
        self,
        script_content: str,
        test_url: str,
        max_retries: int = 2,
        headed: bool = True
    ) -> Tuple[bool, str, List[Dict]]:
        """Run trial with real-time page capture and self-healing.
        
        Args:
            script_content: Test script content
            test_url: URL being tested
            max_retries: Maximum healing attempts
            headed: Run in headed mode
            
        Returns:
            Tuple of (success, logs, healing_attempts)
        """
        from .executor import run_trial_in_framework
        
        healing_attempts = []
        current_script = script_content
        
        for attempt in range(max_retries + 1):
            logger.info(f"[SelfHealing] 🔄 Trial attempt {attempt + 1}/{max_retries + 1}")
            
            # Run trial
            success, logs = run_trial_in_framework(
                current_script,
                self.framework_root,
                headed=headed
            )
            
            if success:
                logger.info(f"[SelfHealing] ✅ Test passed on attempt {attempt + 1}")
                
                # If healing was applied, save the improved script
                if healing_attempts:
                    self._save_healed_script(current_script, "healed_test")
                
                return success, logs, healing_attempts
            
            # Test failed - analyze failure
            failed_locators = extract_failed_locators_from_logs(logs)
            
            if not failed_locators:
                logger.warning("[SelfHealing] ❌ Test failed but no locator errors detected")
                return success, logs, healing_attempts
            
            if attempt >= max_retries:
                logger.warning(f"[SelfHealing] ⚠️ Max retries ({max_retries}) reached")
                return success, logs, healing_attempts
            
            # Capture real page state at failure point
            logger.info(f"[SelfHealing] 🔍 Capturing real page state (found {len(failed_locators)} failed locators)")
            ui_crawl_data = self.capture_page_state_on_failure(test_url)
            
            if "error" in ui_crawl_data:
                logger.error(f"[SelfHealing] Failed to capture page state: {ui_crawl_data['error']}")
                return success, logs, healing_attempts
            
            # Apply self-healing with real UI crawl data
            try:
                logger.info("[SelfHealing] 🔧 Applying Copilot-powered self-healing...")
                
                healed_script = ask_copilot_to_self_heal(
                    failed_script=current_script,
                    logs=logs,
                    ui_crawl=json.dumps(ui_crawl_data, indent=2)
                )
                
                if not healed_script or healed_script == current_script:
                    logger.warning("[SelfHealing] ⚠️ Self-healing returned no changes")
                    return success, logs, healing_attempts
                
                # Log healing details
                healing_attempts.append({
                    "attempt": attempt + 1,
                    "failed_locators": failed_locators,
                    "elements_captured": len(ui_crawl_data.get("elements", [])),
                    "healed": True,
                    "changes": self._diff_scripts(current_script, healed_script)
                })
                
                current_script = healed_script
                logger.info(f"[SelfHealing] ✅ Applied healing fixes, retrying test...")
                
            except Exception as e:
                logger.error(f"[SelfHealing] ❌ Self-healing failed: {e}", exc_info=True)
                healing_attempts.append({
                    "attempt": attempt + 1,
                    "failed_locators": failed_locators,
                    "healed": False,
                    "error": str(e)
                })
                return success, logs, healing_attempts
        
        return success, logs, healing_attempts
    
    def _diff_scripts(self, original: str, healed: str) -> str:
        """Generate a simple diff summary of changes.
        
        Args:
            original: Original script
            healed: Healed script
            
        Returns:
            Summary of changes
        """
        original_lines = original.split('\n')
        healed_lines = healed.split('\n')
        
        changes = []
        for i, (orig, heal) in enumerate(zip(original_lines, healed_lines)):
            if orig != heal:
                changes.append(f"Line {i+1}: {orig.strip()[:50]} → {heal.strip()[:50]}")
        
        return f"{len(changes)} line(s) changed"
    
    def _save_healed_script(self, script_content: str, test_name: str) -> Path:
        """Save healed script to framework tests directory.
        
        Args:
            script_content: Healed script
            test_name: Test name
            
        Returns:
            Path to saved file
        """
        from .core.mcp_client import get_filesystem_mcp
        
        test_dir = self.framework_root / "tests"
        test_file = test_dir / f"{test_name}.spec.ts"
        
        fs_mcp = get_filesystem_mcp()
        fs_mcp.safe_write_file(test_file, script_content, backup=True)
        
        logger.info(f"[SelfHealing] 💾 Saved healed script: {test_file}")
        return test_file


# Example usage
def example_self_healing_flow():
    """Demonstrate complete self-healing flow with Playwright MCP."""
    
    # Example failing test script
    failing_script = """
    import { test, expect } from '@playwright/test';
    
    test('supplier creation test', async ({ page }) => {
      await page.goto('https://fusion.oracle.com/supplier');
      
      // ❌ These locators might be wrong/outdated
      await page.locator('xpath=//button[@id="old-create-btn"]').click();
      await page.locator('#supplier-name-field').fill('Test Supplier');
      await page.locator('css=button.submit').click();
      
      // Verify success
      await expect(page.locator('text=Supplier created')).toBeVisible();
    });
    """
    
    # Initialize self-healing executor
    executor = SelfHealingExecutor(
        framework_root=Path("./framework_repos/my-framework")
    )
    
    # Run with real-time healing
    success, logs, healing_attempts = executor.run_trial_with_real_time_healing(
        script_content=failing_script,
        test_url="https://fusion.oracle.com/supplier",
        max_retries=2,
        headed=False
    )
    
    print(f"\n{'='*60}")
    print(f"Test Result: {'PASSED ✅' if success else 'FAILED ❌'}")
    print(f"{'='*60}")
    print(f"Total Healing Attempts: {len(healing_attempts)}")
    
    for attempt in healing_attempts:
        print(f"\n🔧 Healing Attempt {attempt['attempt']}:")
        print(f"   Failed Locators: {len(attempt['failed_locators'])}")
        print(f"   Elements Captured: {attempt.get('elements_captured', 0)}")
        print(f"   Status: {'SUCCESS ✅' if attempt['healed'] else 'FAILED ❌'}")
        if attempt.get('changes'):
            print(f"   Changes: {attempt['changes']}")
    
    return success, logs, healing_attempts


if __name__ == "__main__":
    example_self_healing_flow()
