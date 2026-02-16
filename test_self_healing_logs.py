"""
Quick test to verify self-healing logging works
"""
from pathlib import Path
from app.self_healing_trial_executor import SelfHealingTrialExecutor
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

# Create executor with metadata
executor = SelfHealingTrialExecutor(recorder_metadata={"actions": []})

# Create dummy test content
test_content = """
import { test } from '@playwright/test';
test('dummy', async ({ page }) => {
  await page.goto('https://example.com');
});
"""

framework_root = Path("framework_repos/f870a1343bdd")

print("\n========== TESTING SELF-HEALING EXECUTOR ==========\n")

# This should show [Self-Healing] logs
result = executor.execute_with_retry(
    test_content,
    framework_root,
    headed=False
)

print(f"\n========== RESULT ==========")
print(f"Success: {result['success']}")
print(f"Attempts: {result['attempts']}")
print(f"Fixes: {len(result.get('fixes_applied', []))}")
