"""Test runtime self-healing functionality."""

import pytest
from pathlib import Path
from app.self_healing_executor import (
    extract_failed_locators_from_logs,
    capture_ui_crawl_on_failure,
    run_trial_with_self_healing
)


def test_extract_failed_locators_from_xpath_error():
    """Test extraction of failed XPath locators from logs."""
    logs = """
    Error: locator('xpath=//button[@id="old-submit-btn"]').click: Timeout 30000ms exceeded.
    =========================== logs ===========================
    waiting for locator('xpath=//button[@id="old-submit-btn"]')
    ============================================================
    """
    
    failed_locators = extract_failed_locators_from_logs(logs)
    
    assert len(failed_locators) > 0
    assert any("old-submit-btn" in loc["locator"] for loc in failed_locators)
    assert failed_locators[0]["type"] == "xpath"


def test_extract_failed_locators_from_css_error():
    """Test extraction of failed CSS selectors."""
    logs = """
    Error: locator('css=#non-existent-element').fill: Timeout 30000ms exceeded.
    waiting for locator('css=#non-existent-element')
    """
    
    failed_locators = extract_failed_locators_from_logs(logs)
    
    assert len(failed_locators) > 0
    assert any("non-existent-element" in loc["locator"] for loc in failed_locators)


def test_extract_failed_locators_from_getby_error():
    """Test extraction of failed getBy* methods."""
    logs = """
    Error: page.getByRole('button', { name: 'Old Button' }).click: Timeout 30000ms exceeded.
    waiting for getByRole('button', { name: 'Old Button' })
    """
    
    failed_locators = extract_failed_locators_from_logs(logs)
    
    assert len(failed_locators) > 0
    assert any("Old Button" in loc["locator"] for loc in failed_locators)


def test_capture_ui_crawl_structure():
    """Test that UI crawl data has expected structure."""
    ui_crawl = capture_ui_crawl_on_failure("test logs")
    
    # Check basic structure
    assert "page_title" in ui_crawl
    assert "url" in ui_crawl
    assert "elements" in ui_crawl
    assert isinstance(ui_crawl["elements"], list)
    
    # Check element structure
    if ui_crawl["elements"]:
        element = ui_crawl["elements"][0]
        assert "tag" in element
        assert "attributes" in element
        assert "xpath" in element or "css" in element


def test_no_failed_locators_in_success_logs():
    """Test that successful test logs don't trigger locator extraction."""
    success_logs = """
    Running 1 test using 1 worker
    ✓ example.spec.ts:3:1 › example test (1.2s)
    1 passed (2.0s)
    """
    
    failed_locators = extract_failed_locators_from_logs(success_logs)
    
    assert len(failed_locators) == 0


def test_multiple_failed_locators():
    """Test extraction of multiple failed locators."""
    logs = """
    Error: locator('xpath=//button[@id="btn1"]').click: Timeout 30000ms exceeded.
    Error: locator('css=#input-field').fill: Timeout 30000ms exceeded.
    Error: page.getByText('Submit').click: Timeout 30000ms exceeded.
    """
    
    failed_locators = extract_failed_locators_from_logs(logs)
    
    # Should find all three failures
    assert len(failed_locators) >= 3


@pytest.mark.skip(reason="Requires actual Playwright setup and framework")
def test_run_trial_with_self_healing_integration():
    """Integration test for self-healing trial run.
    
    This test is skipped by default as it requires:
    - Actual framework repository
    - Playwright installed
    - Valid test script
    """
    
    # Example script with intentionally wrong locator
    failing_script = """
    import { test, expect } from '@playwright/test';
    
    test('example test', async ({ page }) => {
      await page.goto('https://example.com');
      
      // Wrong locator (will fail)
      await page.locator('xpath=//button[@id="nonexistent"]').click();
    });
    """
    
    framework_root = Path("./framework_repos/test-framework")
    
    # This would trigger real self-healing
    success, logs, healing_attempts = run_trial_with_self_healing(
        script_content=failing_script,
        framework_root=framework_root,
        max_retries=1,
        headed=False
    )
    
    # Check that healing was attempted
    assert len(healing_attempts) > 0
    assert "failed_locators" in healing_attempts[0]


def test_self_healing_max_retries():
    """Test that self-healing respects max_retries limit."""
    # This would be tested with a mock that always fails
    # to verify retry limit is enforced
    pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
