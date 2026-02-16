"""
Quick test to verify recorder captures actions before navigation.
Creates a simple HTML page with navigation triggers and tests recording.
"""

import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

def create_test_html():
    """Create a test HTML page with various navigation triggers"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Page 1</title>
    </head>
    <body>
        <h1>Recorder Navigation Test</h1>
        
        <!-- Test 1: Regular link -->
        <a href="page2.html" id="link1">Go to Page 2 (link)</a><br><br>
        
        <!-- Test 2: Button with onclick -->
        <button onclick="window.location.href='page2.html'" id="btn1">
            Go to Page 2 (onclick)
        </button><br><br>
        
        <!-- Test 3: Nested elements -->
        <div onclick="window.location.href='page2.html'" style="cursor: pointer; border: 1px solid black; padding: 10px; width: 200px;" id="div1">
            <span>Nested Click Area</span>
        </div><br><br>
        
        <!-- Test 4: Input before submit -->
        <form action="page2.html" method="get">
            <input type="text" id="name" name="name" placeholder="Enter name"><br>
            <button type="submit" id="submit">Submit Form</button>
        </form><br>
        
        <!-- Test 5: New tab -->
        <a href="page2.html" target="_blank" id="link2">Open in New Tab</a><br><br>
        
        <!-- Test 6: JavaScript window.open -->
        <button onclick="window.open('page2.html', '_blank')" id="btn2">
            Open via window.open()
        </button>
    </body>
    </html>
    """
    
    page2 = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Page 2</title>
    </head>
    <body>
        <h1>Welcome to Page 2</h1>
        <p>You successfully navigated here!</p>
        <a href="page1.html">Back to Page 1</a>
    </body>
    </html>
    """
    
    # Create test pages in temp directory
    test_dir = Path(__file__).parent / 'test_navigation'
    test_dir.mkdir(exist_ok=True)
    
    (test_dir / 'page1.html').write_text(html, encoding='utf-8')
    (test_dir / 'page2.html').write_text(page2, encoding='utf-8')
    
    return test_dir / 'page1.html'


def test_recorder_navigation():
    """Test the recorder with navigation scenarios"""
    from app.run_minimal_recorder import MINIMAL_INJECT
    
    print("Starting recorder navigation test...")
    print("=" * 60)
    
    test_html = create_test_html()
    test_url = f"file:///{test_html.as_posix()}"
    
    recording = {
        'actions': [],
        'pages': {}
    }
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        
        # Navigate to test page
        page.goto(test_url)
        
        # Inject recorder script
        page.evaluate(MINIMAL_INJECT)
        
        print(f"✓ Opened test page: {test_url}")
        print("✓ Injected recorder script")
        print("\nPlease perform these actions manually:")
        print("1. Click 'Go to Page 2 (link)'")
        print("2. Wait 2 seconds")
        print("3. Click back button")
        print("4. Click 'Go to Page 2 (onclick)'")
        print("5. Wait 2 seconds")
        print("\nRecording for 30 seconds...")
        
        # Poll for actions
        start = time.time()
        while time.time() - start < 30:
            try:
                # Get actions
                actions = page.evaluate('() => window.__getRecordedActions ? window.__getRecordedActions() : []')
                if actions:
                    recording['actions'].extend(actions)
                    for action in actions:
                        print(f"  → [{action['action']}] {action.get('visibleText', '')[:50]}")
                
                # Check localStorage
                pending = page.evaluate('() => localStorage.getItem("__minRecPending")')
                if pending:
                    print(f"  ℹ localStorage has {len(json.loads(pending))} pending actions")
                
            except Exception as e:
                print(f"  ⚠ Error polling: {e}")
            
            time.sleep(0.05)  # 50ms polling
        
        # Final drain
        print("\n" + "=" * 60)
        print("Final collection...")
        try:
            final_actions = page.evaluate('() => window.__getRecordedActions ? window.__getRecordedActions() : []')
            recording['actions'].extend(final_actions)
            print(f"✓ Collected {len(final_actions)} final actions")
        except Exception:
            pass
        
        browser.close()
    
    # Analyze results
    print("\n" + "=" * 60)
    print("RESULTS:")
    print("=" * 60)
    print(f"Total actions captured: {len(recording['actions'])}")
    
    # Count action types
    action_types = {}
    for action in recording['actions']:
        atype = action['action']
        action_types[atype] = action_types.get(atype, 0) + 1
    
    print("\nAction breakdown:")
    for atype, count in action_types.items():
        print(f"  - {atype}: {count}")
    
    # Check for clicks before navigation
    clicks_before_nav = [a for a in recording['actions'] if a['action'] == 'click']
    print(f"\nClicks captured: {len(clicks_before_nav)}")
    
    if len(clicks_before_nav) >= 2:
        print("✓ SUCCESS: Captured multiple clicks (including before navigation)")
    elif len(clicks_before_nav) == 1:
        print("⚠ WARNING: Only 1 click captured. Try clicking more buttons.")
    else:
        print("✗ FAIL: No clicks captured! Recorder may have issues.")
    
    # Save results
    output_file = Path(__file__).parent / 'test_navigation' / 'test_results.json'
    output_file.write_text(json.dumps(recording, indent=2), encoding='utf-8')
    print(f"\n✓ Results saved to: {output_file}")
    
    return len(clicks_before_nav) >= 1


if __name__ == '__main__':
    success = test_recorder_navigation()
    exit(0 if success else 1)
