"""Demo script showing self-healing functionality without pytest."""

from app.self_healing_executor import extract_failed_locators_from_logs, capture_ui_crawl_on_failure

print("=" * 60)
print("Runtime Self-Healing Demo")
print("=" * 60)

# Demo 1: Extract failed XPath locators
print("\n1️⃣  Extract Failed XPath Locators")
print("-" * 60)

xpath_logs = """
Error: locator('xpath=//button[@id="old-submit-btn"]').click: Timeout 30000ms exceeded.
=========================== logs ===========================
waiting for locator('xpath=//button[@id="old-submit-btn"]')
============================================================
"""

failed_locators = extract_failed_locators_from_logs(xpath_logs)
print(f"Found {len(failed_locators)} failed locator(s):")
for loc in failed_locators:
    print(f"  • {loc['locator']} ({loc['type']}) - {loc.get('context', '')[:50]}...")

# Demo 2: Extract failed CSS selectors
print("\n2️⃣  Extract Failed CSS Selectors")
print("-" * 60)

css_logs = """
Error: locator('css=#non-existent-element').fill: Timeout 30000ms exceeded.
waiting for locator('css=#non-existent-element')
"""

failed_css = extract_failed_locators_from_logs(css_logs)
print(f"Found {len(failed_css)} failed locator(s):")
for loc in failed_css:
    print(f"  • {loc['locator']} ({loc['type']})")

# Demo 3: Extract getBy* methods
print("\n3️⃣  Extract Failed getBy* Methods")
print("-" * 60)

getby_logs = """
Error: page.getByRole('button', { name: 'Old Button' }).click: Timeout 30000ms exceeded.
waiting for getByRole('button', { name: 'Old Button' })
"""

failed_getby = extract_failed_locators_from_logs(getby_logs)
print(f"Found {len(failed_getby)} failed locator(s):")
for loc in failed_getby:
    print(f"  • {loc['locator']}")

# Demo 4: UI Crawl structure
print("\n4️⃣  UI Crawl Data Structure")
print("-" * 60)

ui_crawl = capture_ui_crawl_on_failure("test logs")
print(f"Captured UI data:")
print(f"  • Page Title: {ui_crawl.get('page_title')}")
print(f"  • URL: {ui_crawl.get('url')}")
print(f"  • Elements: {len(ui_crawl.get('elements', []))}")

if ui_crawl.get('elements'):
    element = ui_crawl['elements'][0]
    print(f"\nExample element:")
    print(f"  • Tag: {element.get('tag')}")
    print(f"  • ID: {element['attributes'].get('id')}")
    print(f"  • Role: {element['attributes'].get('role')}")
    print(f"  • Text: {element.get('text')}")
    print(f"  • XPath: {element.get('xpath')}")

# Demo 5: Multiple failures
print("\n5️⃣  Multiple Failed Locators")
print("-" * 60)

multi_logs = """
Error: locator('xpath=//button[@id="btn1"]').click: Timeout 30000ms exceeded.
Error: locator('css=#input-field').fill: Timeout 30000ms exceeded.
Error: page.getByText('Submit').click: Timeout 30000ms exceeded.
"""

multi_failed = extract_failed_locators_from_logs(multi_logs)
print(f"Found {len(multi_failed)} failed locators:")
for i, loc in enumerate(multi_failed, 1):
    print(f"  {i}. {loc['locator']} ({loc['type']})")

# Summary
print("\n" + "=" * 60)
print("✅ All demos completed successfully!")
print("=" * 60)
print("\n📖 How Self-Healing Works:")
print("""
1. Test fails with incorrect XPath/locator
2. extract_failed_locators_from_logs() detects failures
3. capture_page_state_on_failure() captures real page with Playwright MCP
4. ask_copilot_to_self_heal() generates better locators using VS Code Copilot API + MS Docs MCP
5. Uses generated flows from app/generated_flow (JSON) for context
6. Test retries automatically with healed script
7. If success, healed script is saved for future use

See docs/RUNTIME_SELF_HEALING.md for complete guide!
""")
