import json
import sys
import os

def remove_consecutive_duplicates(actions):
    """Remove consecutive duplicate actions and checkbox input/change events.
    
    This preserves the original recorder content except for:
    - Removing consecutive duplicates (same element AND same action)
    - Removing input/change actions on checkboxes that follow any action on the same checkbox
    """
    if not actions:
        return []
    
    deduplicated = [actions[0]]
    
    for action in actions[1:]:
        # Get current action details
        current_elem = action.get('element', {})
        current_selector = current_elem.get('selector', {})
        current_css = current_selector.get('css', '') or current_elem.get('cssPath', '')
        current_xpath = current_selector.get('xpath', '') or current_elem.get('xpath', '')
        current_action = action.get('action', '')
        current_html = current_elem.get('html', '')
        
        # Get previous action details
        prev = deduplicated[-1]
        prev_elem = prev.get('element', {})
        prev_selector = prev_elem.get('selector', {})
        prev_css = prev_selector.get('css', '') or prev_elem.get('cssPath', '')
        prev_xpath = prev_selector.get('xpath', '') or prev_elem.get('xpath', '')
        prev_action = prev.get('action', '')
        
        # Check if current element is a checkbox
        is_checkbox = 'type="checkbox"' in current_html or 'type="radio"' in current_html
        
        # Skip input/change actions for checkboxes if on same element as previous action
        if is_checkbox and current_action in ['input', 'change'] and current_css == prev_css:
            continue
        
        # Skip if BOTH the element AND action type are the same
        if (current_css, current_xpath, current_action) == (prev_css, prev_xpath, prev_action):
            continue
            
        deduplicated.append(action)
    
    # Add step numbers
    for idx, action in enumerate(deduplicated, start=1):
        action['step'] = idx
    
    return deduplicated

def transform_to_refined(metadata_path, output_path):
    """Transform recorder metadata to refined format.
    
    The refined content is the same as recorder content, except:
    - Consecutive duplicate steps are removed
    - Steps are stored in 'steps' field instead of 'actions'
    """
    with open(metadata_path, 'r', encoding='utf-8') as f:
        metadata = json.load(f)
    
    # Remove consecutive duplicates
    refined_actions = remove_consecutive_duplicates(metadata['actions'])
    
    # Create refined structure - keep original metadata intact, just rename actions to steps
    refined = metadata.copy()
    refined["refinedVersion"] = "2025.10"
    refined["steps"] = refined_actions
    
    # Remove the old 'actions' field since we renamed it to 'steps'
    if 'actions' in refined:
        del refined['actions']
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(refined, f, indent=2, ensure_ascii=False)
    
    print(f"Original actions: {len(metadata['actions'])}")
    print(f"Refined steps: {len(refined_actions)}")
    print(f"Removed {len(metadata['actions']) - len(refined_actions)} consecutive duplicates")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python transform_metadata.py <flow_id>")
        print("Example: python transform_metadata.py poiuy")
        sys.exit(1)
    
    flow_id = sys.argv[1]
    metadata_path = f"recordings/{flow_id}/metadata.json"
    output_path = f"app/generated_flows/{flow_id}-{flow_id}.refined.full.json"
    
    if not os.path.exists(metadata_path):
        print(f"Error: {metadata_path} not found")
        sys.exit(1)
    
    transform_to_refined(metadata_path, output_path)
