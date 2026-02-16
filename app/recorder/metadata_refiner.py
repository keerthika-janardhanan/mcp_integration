"""
Metadata Refiner - Cleans up recorded metadata by removing degraded actions
"""
import json
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime


def refine_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Refine metadata by removing degraded actions and consolidating data.
    
    Args:
        metadata: Raw metadata dictionary
        
    Returns:
        Refined metadata dictionary
    """
    # Handle both old format (pages as list with nested actions) and new format (actions at top level)
    if isinstance(metadata.get("pages"), list):
        # Old format: pages is a list with actions nested
        actions_list = []
        for page in metadata.get("pages", []):
            actions_list.extend(page.get("actions", []))
    else:
        # New format: actions at top level, pages is a dict
        actions_list = metadata.get("actions", [])
    
    refined_pages = []
    total_actions = 0
    action_types = {}
    
    # Process actions (using dummy loop variable since we're processing all at once)
    if actions_list:
        actions = actions_list
        
        # Filter out degraded actions (no valid selectors)
        valid_actions = []
        for action in actions:
            selectors = action.get("selectorStrategies", {})
            # Keep only actions with at least one valid selector
            if selectors and any(v for v in selectors.values() if v):
                # Simplify action structure
                refined_action = {
                    "actionId": action.get("actionId"),
                    "type": action.get("type") or action.get("action"),
                    "timestamp": action.get("timestamp"),
                }
                
                # Add element info (minimal)
                element = action.get("element", {})
                refined_element = {
                    "tag": element.get("tag"),
                }
                if element.get("id"):
                    refined_element["id"] = element["id"]
                if element.get("role"):
                    refined_element["role"] = element["role"]
                if element.get("ariaLabel"):
                    refined_element["ariaLabel"] = element["ariaLabel"]
                if element.get("placeholder"):
                    refined_element["placeholder"] = element["placeholder"]
                if element.get("text"):
                    refined_element["text"] = element["text"]
                if element.get("className"):
                    refined_element["className"] = element["className"]
                if element.get("attributes", {}).get("value"):
                    refined_element["value"] = element["attributes"]["value"]
                    
                refined_action["element"] = refined_element
                refined_action["selectorStrategies"] = selectors
                
                # Add description
                refined_action["description"] = _generate_description(refined_action)
                
                # Add inputSummary if present
                if action.get("inputSummary"):
                    refined_action["inputSummary"] = action["inputSummary"]
                
                valid_actions.append(refined_action)
                total_actions += 1
                
                action_type = refined_action["type"]
                action_types[action_type] = action_types.get(action_type, 0) + 1
        
        # Only include pages with valid actions
        if valid_actions:
            refined_pages.append({
                "pageId": page.get("pageId"),
                "pageUrl": page.get("pageUrl"),
                "pageTitle": page.get("pageTitle"),
                "actions": valid_actions
            })
    
    # Calculate duration
    session = metadata.get("session", {})
    duration = None
    if session.get("startedAt") and session.get("endedAt"):
        try:
            start = datetime.fromisoformat(session["startedAt"].replace("+00:00", ""))
            end = datetime.fromisoformat(session["endedAt"].replace("+00:00", ""))
            duration = f"{(end - start).total_seconds():.2f} seconds"
        except:
            pass
    
    # Build refined metadata
    refined = {
        "metadataVersion": metadata.get("metadataVersion"),
        "flowId": metadata.get("flowId"),
        "flowName": metadata.get("flowName") or metadata.get("flowId"),
        "runTimestamp": metadata.get("runTimestamp"),
        "environment": metadata.get("environment"),
        "pages": refined_pages,
        "session": {
            "id": session.get("id"),
            "startedAt": session.get("startedAt"),
            "endedAt": session.get("endedAt"),
        },
        "options": {
            "browser": metadata.get("options", {}).get("browser"),
            "headless": metadata.get("options", {}).get("headless"),
            "slowMo": metadata.get("options", {}).get("slowMo"),
            "recordTrace": metadata.get("options", {}).get("recordTrace"),
            "url": metadata.get("options", {}).get("url"),
        },
        "artifacts": metadata.get("artifacts", {}),
        "summary": {
            "totalActions": total_actions,
            "totalPages": len(refined_pages),
            "actionsByType": action_types,
            "notes": [
                "Auto-refined: Removed degraded actions with incomplete selectors",
                "Retained only actions with valid selector strategies",
            ]
        }
    }
    
    if duration:
        refined["session"]["duration"] = duration
    
    return refined


def _generate_description(action: Dict[str, Any]) -> str:
    """Generate human-readable description for action."""
    action_type = action.get("type", "")
    element = action.get("element", {})
    tag = element.get("tag", "")
    
    # Build description
    if action_type == "click":
        if element.get("value"):
            return f"Click {element['value']} button"
        elif element.get("ariaLabel"):
            return f"Click {element['ariaLabel']}"
        elif element.get("text"):
            return f"Click {element['text']}"
        elif element.get("placeholder"):
            return f"Click {element['placeholder']} field"
        elif tag == "input" and element.get("role") == "textbox":
            return f"Click input field"
        elif tag == "input" and element.get("role") == "checkbox":
            return f"Click checkbox"
        elif tag == "button":
            return f"Click button"
        else:
            return f"Click {tag}"
    elif action_type == "fill":
        return f"Fill {element.get('placeholder', 'input field')}"
    elif action_type == "type":
        return f"Type into {element.get('placeholder', 'field')}"
    else:
        return f"{action_type.capitalize()} {tag}"


def refine_metadata_file(metadata_path: Path) -> Path:
    """
    Refine metadata file and save as *_refined.json.
    
    Args:
        metadata_path: Path to metadata.json
        
    Returns:
        Path to refined metadata file
    """
    with open(metadata_path, 'r', encoding='utf-8') as f:
        metadata = json.load(f)
    
    refined = refine_metadata(metadata)
    
    # Save refined version
    refined_path = metadata_path.parent / "metadata_refined.json"
    with open(refined_path, 'w', encoding='utf-8') as f:
        json.dump(refined, f, indent=2, ensure_ascii=False)
    
    return refined_path


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
        if path.is_dir():
            path = path / "metadata.json"
        refined_path = refine_metadata_file(path)
        print(f"✅ Refined metadata saved to: {refined_path}")
