"""Test payload generation to diagnose pages/locators/testDataMapping issues"""
import sys
import json
import logging
from pathlib import Path

# Setup logging to see what's happening
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

sys.path.insert(0, str(Path(__file__).parent))

from app.generators.agentic_script_agent import AgenticScriptAgent, FrameworkProfile

# Test scenario
scenario = "Generate automation script for test93"
accepted_preview = """1. input | Enter your email, phone, or Skype.
2. click | Next
3. input | Enter the password for 2218532@cognizant.com
4. checkbox | Keep me signed in
5. click | Yes
6. input | username field
7. click | Submit"""

# Create agent
agent = AgenticScriptAgent()

# Create a minimal framework profile (no actual repo needed for this test)
class MockFramework:
    def __init__(self):
        self.locators_dir = Path("locators")
        self.pages_dir = Path("pages")
        self.tests_dir = Path("tests")
        self.root = Path(".")
    
    def summary(self):
        return "Mock framework for testing"
    
    def sample_snippet(self, dir_path, limit_files=2, max_chars=800):
        return "// Sample code\nexport class SamplePage {}"

framework = MockFramework()

print("\n" + "="*80)
print("Testing Payload Generation")
print("="*80)

try:
    payload = agent.generate_script_payload(scenario, framework, accepted_preview)
    
    print(f"\n✓ Payload generated successfully!")
    print(f"\nPayload keys: {list(payload.keys())}")
    print(f"\nLocators: {len(payload.get('locators', []))} files")
    for loc in payload.get('locators', []):
        print(f"  - {loc.get('path', 'NO PATH')}: {len(loc.get('content', ''))} chars")
    
    print(f"\nPages: {len(payload.get('pages', []))} files")
    for page in payload.get('pages', []):
        print(f"  - {page.get('path', 'NO PATH')}: {len(page.get('content', ''))} chars")
    
    print(f"\nTests: {len(payload.get('tests', []))} files")
    for test in payload.get('tests', []):
        print(f"  - {test.get('path', 'NO PATH')}: {len(test.get('content', ''))} chars")
    
    print(f"\nTest Data Mapping: {len(payload.get('testDataMapping', []))} fields")
    for mapping in payload.get('testDataMapping', []):
        print(f"  - {mapping.get('columnName', 'NO NAME')}: {mapping.get('actionType', 'NO ACTION')} ({mapping.get('occurrences', 0)} occurrences)")
    
    # Save payload to file for inspection
    output_file = Path(__file__).parent / "test_payload_output.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2)
    print(f"\n✓ Full payload saved to: {output_file}")
    
except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
