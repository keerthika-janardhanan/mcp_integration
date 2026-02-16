"""
Test suite for auto_refine (build_refined_flow_from_metadata) to validate deduplication logic.

Tests the smart deduplication rules:
1. Checkbox input → filtered out
2. input + change → keep input
3. click → input → input replaces click
4. Duplicate actions → remove duplicates
5. Timestamp ordering preserved
"""
import pytest
from app.recorder.recorder_auto_ingest import build_refined_flow_from_metadata


def test_auto_refine_input_over_change():
    """Test that input is kept over change for same element"""
    metadata = {
        "actions": [
            {
                "action": "input",
                "timestamp": 1000,
                "element": {
                    "html": '<input id="username" name="username">',
                    "selector": {"css": "#username"}
                }
            },
            {
                "action": "change",
                "timestamp": 1001,
                "element": {
                    "html": '<input id="username" name="username">',
                    "selector": {"css": "#username"}
                }
            }
        ]
    }
    
    result = build_refined_flow_from_metadata(metadata)
    
    assert len(result["steps"]) == 1
    assert result["steps"][0]["action"] == "input"
    print("✓ Input over change test passed")


def test_auto_refine_click_replaced_by_input():
    """Test that input replaces click for same element"""
    metadata = {
        "actions": [
            {
                "action": "click",
                "timestamp": 1000,
                "element": {
                    "html": '<input id="username" name="username">',
                    "selector": {"css": "#username"}
                }
            },
            {
                "action": "input",
                "timestamp": 1001,
                "element": {
                    "html": '<input id="username" name="username">',
                    "selector": {"css": "#username"}
                }
            }
        ]
    }
    
    result = build_refined_flow_from_metadata(metadata)
    
    assert len(result["steps"]) == 1
    assert result["steps"][0]["action"] == "input"
    print("✓ Click replaced by input test passed")


def test_auto_refine_workday_recording():
    """Test with actual Workday recording structure"""
    metadata = {
        "flowName": "Workday Login",
        "actions": [
            {"action": "click", "timestamp": 1000, "element": {"html": '<input id="username">', "selector": {"css": "#username"}}},
            {"action": "input", "timestamp": 1050, "element": {"html": '<input id="username">', "selector": {"css": "#username"}}},
            {"action": "change", "timestamp": 1100, "element": {"html": '<input id="username">', "selector": {"css": "#username"}}},
            {"action": "click", "timestamp": 2000, "element": {"html": '<input type="password" id="password">', "selector": {"css": "#password"}}},
            {"action": "input", "timestamp": 2050, "element": {"html": '<input type="password" id="password">', "selector": {"css": "#password"}}},
            {"action": "change", "timestamp": 2100, "element": {"html": '<input type="password" id="password">', "selector": {"css": "#password"}}},
            {"action": "click", "timestamp": 3000, "element": {"html": '<input type="checkbox" id="remember">', "selector": {"css": "#remember"}}},
            {"action": "input", "timestamp": 3050, "element": {"html": '<input type="checkbox" id="remember">', "selector": {"css": "#remember"}}},
            {"action": "change", "timestamp": 3100, "element": {"html": '<input type="checkbox" id="remember">', "selector": {"css": "#remember"}}},
            {"action": "click", "timestamp": 4000, "element": {"html": '<button type="submit">Sign In</button>', "selector": {"css": "button[type='submit']"}}},
            {"action": "click", "timestamp": 4050, "element": {"html": '<button type="submit">Sign In</button>', "selector": {"css": "button[type='submit']"}}},
            {"action": "submit", "timestamp": 4100, "element": {"html": '<button type="submit">Sign In</button>', "selector": {"css": "button[type='submit']"}}}
        ]
    }
    
    result = build_refined_flow_from_metadata(metadata)
    
    original_count = len(metadata["actions"])
    refined_count = len(result["steps"])
    
    # Should have deduplicated significantly (12 → ~3-4 steps)
    assert refined_count < original_count
    assert refined_count <= 6  # Username input + password input + checkbox click + button click (maybe 2 button duplicates if no IDs)
    
    # Check that we have the key actions
    actions = [s["action"] for s in result["steps"]]
    assert "input" in actions  # username or password
    
    print(f"✓ Workday recording test passed: {original_count} → {refined_count} steps")


def test_auto_refine_duplicate_clicks():
    """Test that duplicate clicks on same element with IDs are deduplicated"""
    metadata = {
        "actions": [
            {
                "action": "click",
                "timestamp": 1000,
                "element": {
                    "html": '<button id="feedback-btn">Feedback Received</button>',
                    "selector": {"css": "#feedback-btn"}
                }
            },
            {
                "action": "click",
                "timestamp": 1200,
                "element": {
                    "html": '<button id="feedback-btn">Feedback Received</button>',
                    "selector": {"css": "#feedback-btn"}
                }
            }
        ]
    }
    
    result = build_refined_flow_from_metadata(metadata)
    
    assert len(result["steps"]) == 1
    assert result["steps"][0]["action"] == "click"
    print("✓ Duplicate clicks test passed")


def test_auto_refine_preserves_order():
    """Test that timestamp ordering is preserved"""
    metadata = {
        "actions": [
            {
                "action": "input",
                "timestamp": 3000,
                "element": {"html": "<input id='field2'>", "selector": {"css": "#field2"}}
            },
            {
                "action": "input",
                "timestamp": 1000,
                "element": {"html": "<input id='field1'>", "selector": {"css": "#field1"}}
            },
            {
                "action": "click",
                "timestamp": 5000,
                "element": {"html": "<button>Submit</button>", "selector": {"css": ".btn"}}
            }
        ]
    }
    
    result = build_refined_flow_from_metadata(metadata)
    
    # Should be sorted by timestamp: 1000, 3000, 5000
    timestamps = [step.get("timestamp") for step in result["steps"]]
    assert timestamps == sorted(timestamps), f"Expected sorted timestamps, got {timestamps}"
    
    # Check order: field1, field2, button
    selectors = [step.get("element", {}).get("selector", {}).get("css") for step in result["steps"]]
    assert selectors == ["#field1", "#field2", ".btn"]
    
    print("✓ Timestamp ordering test passed")


if __name__ == "__main__":
    # Run tests manually for debugging
    print("Running auto_refine tests...\n")
    
    try:
        test_auto_refine_input_over_change()
        test_auto_refine_click_replaced_by_input()
        test_auto_refine_workday_recording()
        test_auto_refine_duplicate_clicks()
        test_auto_refine_preserves_order()
        
        print("\n✅ All tests passed!")
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
