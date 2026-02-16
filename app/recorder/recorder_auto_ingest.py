from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    from .recorder_enricher import GENERATED_DIR, slugify, _describe_step  # type: ignore
except ImportError:  # pragma: no cover - allow running as script
    from recorder_enricher import GENERATED_DIR, slugify, _describe_step  # type: ignore

REFINED_VERSION = "2025.10"

# LLM Configuration from environment
ENABLE_LLM_FEATURES = os.getenv("ENABLE_LLM_FEATURES", "true").lower() == "true"


def _first_non_empty(*values: Optional[Any]) -> str:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, (int, float)):
            return str(value)
        if isinstance(value, Iterable) and not isinstance(value, (str, bytes, dict)):
            text = ", ".join(str(item) for item in value if item)
            if text.strip():
                return text.strip()
    return ""


def _normalise_playwright_selector(selector: Any, element: Dict[str, Any]) -> str:
    if isinstance(selector, str) and selector.strip():
        return selector.strip()
    if isinstance(selector, dict):
        by_role = selector.get("byRole")
        if isinstance(by_role, dict):
            role = by_role.get("role")
            name = by_role.get("name")
            if role and name:
                return f'getByRole("{role}", name="{name}")'
        elif isinstance(by_role, str) and by_role.strip():
            return by_role.strip()
        by_label = selector.get("byLabel")
        if isinstance(by_label, str) and by_label.strip():
            return by_label.strip()
        by_text = selector.get("byText")
        if isinstance(by_text, str) and by_text.strip():
            return by_text.strip()
        by_placeholder = selector.get("byPlaceholder")
        if isinstance(by_placeholder, str) and by_placeholder.strip():
            return by_placeholder.strip()
    stable = element.get("stableSelector")
    if stable:
        return str(stable)
    css_path = element.get("cssPath")
    if css_path:
        return str(css_path)
    xpath = element.get("xpath")
    if xpath:
        return str(xpath)
    return ""


def _collect_xpath_candidates(*values: Optional[str]) -> List[str]:
    seen: List[str] = []
    for raw in values:
        if not raw:
            continue
        candidate = str(raw)
        if candidate and candidate not in seen:
            seen.append(candidate)
    return seen


def _compose_locators(action: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
    selectors = action.get("selectorStrategies") or {}
    element = action.get("element") or {}

    # New format: element.selector contains css/xpath/playwright
    selector_obj = element.get("selector") or {}
    
    playwright_selector = (
        selectors.get("aria") 
        or selectors.get("playwright") 
        or selector_obj.get("playwright")  # New format
        or element.get("playwright")  # Old format
    )
    playwright_str = _normalise_playwright_selector(playwright_selector, element)
    
    # CSS: try selectorStrategies first, then element.selector, then element.cssPath
    css = selectors.get("css") or selector_obj.get("css") or element.get("cssPath") or ""
    
    # XPath: try selectorStrategies first, then element.selector, then element.xpath
    xpath = selectors.get("xpath") or selector_obj.get("xpath") or ""
    element_xpath = element.get("xpath") or ""
    labels_raw = element.get("labels")
    if isinstance(labels_raw, (list, tuple, set)):
        labels = ", ".join(str(label) for label in labels_raw if label)
    else:
        labels = str(labels_raw or "")
    heading = _first_non_empty(element.get("nearestHeading"), element.get("heading"))
    page_heading = _first_non_empty(element.get("pageHeading"), element.get("page_heading"))

    locators: Dict[str, Any] = {
        "playwright": playwright_str,
        "stable": element.get("stableSelector") or css or element_xpath or xpath or "",
        "xpath": xpath,
        "xpath_candidates": _collect_xpath_candidates(xpath, element_xpath),
        "raw_xpath": element_xpath or xpath,
        "css": css,
        "title": element.get("title") or "",
        "labels": labels,
        "role": element.get("role") or "",
        "name": _first_non_empty(element.get("name"), element.get("ariaLabel")),
        "tag": element.get("tag") or "",
        "heading": heading,
        "page_heading": page_heading,
    }

    element_label = _first_non_empty(labels, locators["name"], locators["title"], locators["tag"])
    return locators, element_label


def _is_valid_selector(selector: str, css: str = "", xpath: str = "") -> bool:
    """Check if a selector is valid and not too generic to be useful."""
    if not selector:
        return False
    
    selector_lower = selector.lower().strip()
    
    # Reject generic element selectors
    invalid_patterns = [
        "body", "html", "document", "window",
        "html > body", "body.", "html.body"
    ]
    
    for pattern in invalid_patterns:
        if selector_lower == pattern or selector_lower.startswith(pattern + " ") or selector_lower.startswith(pattern + "."):
            return False
    
    # Reject XPath that only targets html or body
    if xpath:
        xpath_lower = xpath.lower()
        if xpath_lower in ("/html[1]", "/html[1]/body[1]", "//html", "//body", "/html", "/body"):
            return False
        # Reject XPath that ends with just /body[1]
        if xpath_lower.endswith("/body[1]") and xpath_lower.count("/") <= 3:
            return False
    
    # Reject CSS that only targets body or html
    if css:
        css_lower = css.lower().strip()
        if css_lower in ("body", "html", "html > body"):
            return False
        # Reject selectors like "body.someclass" without descendants
        if css_lower.startswith("body") and ">" not in css_lower and " " not in css_lower[4:]:
            return False
    
    return True


def _convert_action(action: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    action_type = (action.get("type") or action.get("action") or "").lower()
    extra = action.get("extra") or {}
    selectors = action.get("selectorStrategies") or {}
    element = action.get("element") or {}

    mapped_action = None
    value = None

    # Handle minimal recorder format (input/change/click)
    if action_type in ("change", "input"):
        # Check if element is checkbox - treat as click
        element_type = element.get("type") or ""
        if element_type.lower() == "checkbox":
            mapped_action = "click"
            value = ""
        else:
            mapped_action = "fill"
            # Try extra.value first (old format), then element.value (new format)
            value = extra.get("valueMasked") or extra.get("value") or element.get("value") or ""
    elif action_type == "click":
        mapped_action = "click"
        value = ""
    elif action_type == "press":
        key = extra.get("key") or extra.get("code") or element.get("key")
        if not key:
            return None
        mapped_action = "press"
        value = str(key)
    else:
        return None

    locators, element_label = _compose_locators(action)
    
    # Handle minimal recorder selector format
    selector_obj = element.get("selector") or {}
    playwright_selectors = selector_obj.get("playwright") or {}
    
    # Only try to extract from playwright_selectors if it's a dict
    selector = None
    
    # Priority 1: Playwright semantic selectors
    if isinstance(playwright_selectors, dict):
        selector = (
            playwright_selectors.get("byRole")
            or playwright_selectors.get("byLabel")
            or playwright_selectors.get("byText")
            or playwright_selectors.get("byPlaceholder")
        )
    
    # Priority 2: CSS selector or other fallback sources
    if not selector:
        selector = (
            selector_obj.get("css")
            or selector_obj.get("xpath")
            or selectors.get("aria")
            or selectors.get("playwright")
            or locators.get("stable")
        )
    if not selector:
        selector = locators.get("css") or locators.get("raw_xpath") or ""

    # Get CSS and XPath for validation
    css_selector = selector_obj.get("css") or locators.get("css", "")
    xpath_selector = selector_obj.get("xpath") or locators.get("raw_xpath", "") or locators.get("xpath", "")
    
    # Validate selector - reject generic body/html selectors
    if not _is_valid_selector(selector, css_selector, xpath_selector):
        return None

    if not selector:
        return None

    notes = action.get("notes") or []
    description = "; ".join(n for n in notes if n)

    raw_step = {
        "action": mapped_action,
        "selector": selector,
        "value": str(value or ""),
        "url": action.get("pageUrl"),
        "description": description,
    }

    element_entry = {
        "tag": locators.get("tag", ""),
        "title": locators.get("title", ""),
        "label": element_label,
        "role": locators.get("role", ""),
        "name": locators.get("name", "") or element_label,
        "xpath": selector_obj.get("xpath") or locators.get("raw_xpath", "") or locators.get("xpath", ""),
        "css": selector_obj.get("css") or locators.get("css", ""),
        "heading": locators.get("heading", ""),
        "page_heading": locators.get("page_heading", ""),
    }

    data_label = element_label or locators.get("tag", "") or "Field"

    return {
        "raw": raw_step,
        "locators": locators,
        "element": element_entry,
        "data_label": data_label,
        "value": str(value or ""),
        "metadata": {
            "actionId": action.get("actionId"),
            "type": action_type,
        },
    }


def _filter_auth_steps(actions: List[Dict[str, Any]], original_url: Optional[str]) -> List[Dict[str, Any]]:
    """Filter out authentication steps before reaching the original URL.
    
    Strategy:
    1. Identify auth domains (microsoft, okta, etc.)
    2. Skip ALL actions until we're back on the target domain
    3. Keep only actions on the target domain
    """
    if not original_url:
        return actions
    
    from urllib.parse import urlparse
    try:
        target_parsed = urlparse(original_url)
        target_domain = target_parsed.netloc.lower()
        if not target_domain:
            return actions
    except Exception:
        return actions
    
    # Auth provider patterns
    auth_patterns = [
        'login.microsoftonline',
        'microsoftonline.com',
        'login.microsoft',
        'okta.com',
        'auth0.com',
        'oauth',
        'sso.',
        'saml',
    ]
    
    filtered = []
    for action in actions:
        page_url = action.get("pageUrl") or ""
        
        try:
            current_domain = urlparse(page_url).netloc.lower()
            
            # Skip if on auth domain
            if any(pattern in current_domain for pattern in auth_patterns):
                continue
            
            # Keep if on target domain or subdomain
            if target_domain in current_domain or current_domain in target_domain:
                filtered.append(action)
        except Exception:
            # If URL parsing fails, keep the action
            filtered.append(action)
    
    return filtered if filtered else actions


def _deduplicate_actions(actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Smart deduplication with element grouping and parent-child detection.
    
    Strategy:
    - Group actions by element ID/name (infinite time for same element)
    - Group clicks within 1 second (catches span-inside-button)
    - Priority: input > click > change > submit
    """
    if not actions:
        return []
    
    import re
    
    def get_element_id(action: Dict[str, Any]) -> str:
        """Get unique element identifier from id, name, or test-id ONLY.
        
        Don't use CSS/XPath as fallback - they're too specific for spans inside buttons.
        """
        html = action.get("element", {}).get("html", "")
        
        # Try data-testid first (most stable)
        testid = re.search(r'data-testid="([^"]+)"', html)
        if testid:
            return f"testid:{testid.group(1)}"
        
        # Try id attribute
        id_match = re.search(r'\bid="([^"]+)"', html)
        if id_match:
            return f"id:{id_match.group(1)}"
        
        # Try name attribute
        name_match = re.search(r'name="([^"]+)"', html)
        if name_match:
            return f"name:{name_match.group(1)}"
        
        # Try aria-label (useful for Workday buttons)
        label = re.search(r'aria-label="([^"]+)"', html)
        if label:
            return f"label:{label.group(1)}"
        
        # No stable ID - return empty string
        return ""
    
    def is_checkbox(html: str) -> bool:
        return 'type="checkbox"' in html or 'type="radio"' in html
    
    def is_form_input(html: str) -> bool:
        return '<input' in html or '<textarea' in html
    
    def are_related_clicks(action1: Dict, action2: Dict) -> bool:
        """Check if two clicks are related (span inside button, etc.)"""
        time1 = action1.get("timestamp", 0)
        time2 = action2.get("timestamp", 0)
        
        # Must be within 1 second
        if abs(time2 - time1) > 1000:
            return False
        
        # Check if visible text matches (span inside button scenario)
        text1 = action1.get("visibleText", "").strip()
        text2 = action2.get("visibleText", "").strip()
        
        return text1 and text1 == text2
    
    # Pass 1: Group actions by element ID
    element_groups = {}
    no_id_actions = []
    
    for action in actions:
        elem_id = get_element_id(action)
        if elem_id:
            if elem_id not in element_groups:
                element_groups[elem_id] = []
            element_groups[elem_id].append(action)
        else:
            no_id_actions.append(action)
    
    # Pass 2: Deduplicate each element group
    deduplicated = []
    processed_indices = set()
    
    for elem_id, group in element_groups.items():
        if len(group) == 1:
            action = group[0]
            action_type = action.get("action", "")
            html = action.get("element", {}).get("html", "")
            
            # Skip checkbox input/change
            if is_checkbox(html) and action_type in ["input", "change"]:
                continue
            
            deduplicated.append(action)
        else:
            # Multiple actions on same element - apply priority
            html = group[0].get("element", {}).get("html", "")
            action_map = {a.get("action", ""): a for a in group}
            
            if is_checkbox(html):
                # Checkbox: keep only click
                if "click" in action_map:
                    deduplicated.append(action_map["click"])
            elif is_form_input(html):
                # Form input: keep input, discard click/change
                if "input" in action_map:
                    deduplicated.append(action_map["input"])
            else:
                # Button/link: keep click, discard submit
                if "click" in action_map:
                    deduplicated.append(action_map["click"])
                elif "submit" in action_map:
                    deduplicated.append(action_map["submit"])
                else:
                    deduplicated.append(group[0])
    
    # Pass 3: Handle actions without IDs (detect parent-child clicks)
    for action in no_id_actions:
        # Skip if this action is a duplicate of an existing action
        is_duplicate = False
        
        if action.get("action") == "click":
            for existing in deduplicated:
                if existing.get("action") == "click" and are_related_clicks(action, existing):
                    is_duplicate = True
                    break
        
        if not is_duplicate:
            deduplicated.append(action)
    
    # Sort by timestamp
    deduplicated.sort(key=lambda a: a.get("timestamp", 0))
    
    return deduplicated
    
    return deduplicated


def build_refined_flow_from_metadata(
    metadata: Dict[str, Any],
    flow_name: Optional[str] = None,
    session_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Build refined flow from recorder metadata.
    
    The refined content is the same as recorder content, except:
    - Consecutive duplicate steps are removed
    - Steps are stored in 'steps' field instead of 'actions'
    - A 'refinedVersion' field is added
    """
    # Ensure metadata is a dict, not a string
    if isinstance(metadata, str):
        raise ValueError(f"metadata must be a dict, got string: {metadata[:100]}")
    
    actions = metadata.get("actions") or []
    if not actions:
        raise ValueError("Recorder metadata does not contain any actions.")

    # Try to read flow name from flow_name.txt file first
    flow_name_from_file = None
    if session_dir:
        flow_name_file = Path(session_dir) / "flow_name.txt"
        if flow_name_file.exists():
            try:
                flow_name_from_file = flow_name_file.read_text(encoding="utf-8").strip()
            except Exception:
                pass
    
    resolved_flow_name = flow_name or flow_name_from_file or metadata.get("flowName") or metadata.get("flow_name") or metadata.get("flowId") or metadata.get("flow_id") or "Recorder Flow"
    
    # Sort actions by timestamp to ensure chronological order
    def _get_timestamp(action: Dict[str, Any]) -> str:
        ts = action.get("timestamp") or action.get("timestampEpochMs") or action.get("receivedAt") or ""
        return str(ts)
    
    try:
        actions = sorted(actions, key=_get_timestamp)
    except Exception:
        pass
    
    # Remove consecutive duplicates while preserving sequence
    refined_actions = _deduplicate_actions(actions)
    
    # Add step numbers to refined actions
    for idx, action in enumerate(refined_actions, start=1):
        action["step"] = idx
    
    # Create refined structure - keep original metadata intact
    refined_flow = metadata.copy()
    refined_flow["refinedVersion"] = REFINED_VERSION
    refined_flow["flow_name"] = resolved_flow_name
    refined_flow["steps"] = refined_actions
    
    # Remove the old 'actions' field since we renamed it to 'steps'
    if 'actions' in refined_flow:
        del refined_flow['actions']
    
    return refined_flow


def auto_refine_and_ingest(
    session_dir: str | Path,
    metadata: Dict[str, Any],
    *,
    flow_name: Optional[str] = None,
    ingest: bool = True,
) -> Dict[str, Any]:
    session_path = Path(session_dir)
    
    # Track original action count for filtering statistics
    # Priority: options.url > options.originalUrl > startUrl
    options = metadata.get("options") or {}
    original_url = (
        options.get("url") 
        or options.get("originalUrl") 
        or metadata.get("startUrl")
        or metadata.get("start_url")
    )
    total_actions = len(metadata.get("actions") or [])
    
    refined_flow = build_refined_flow_from_metadata(metadata, flow_name=flow_name, session_dir=session_path)
    
    # Log deduplication statistics
    refined_steps = len(refined_flow.get("steps") or [])
    filtered_count = total_actions - refined_steps
    if filtered_count > 0:
        print(f"[auto_refine] Removed {filtered_count} consecutive duplicate steps")
        print(f"[auto_refine] Refined flow contains {refined_steps} unique steps")

    resolved_flow_name = refined_flow["flow_name"]
    slug = slugify(resolved_flow_name)
    session_suffix = session_path.name or metadata.get("flowId") or "session"
    output_path = GENERATED_DIR / f"{slug}-{session_suffix}.refined.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as fh:
        json.dump(refined_flow, fh, indent=2, ensure_ascii=False)
    
    # Skip clean metadata generation for now - metadata_refiner expects different format
    # The refined.json is the main output; clean.json was just a bonus
    # TODO: Update metadata_refiner to handle new minimal metadata format

    ingest_stats: Optional[Dict[str, Any]] = None
    ingest_error: Optional[str] = None
    if ingest:
        try:
            from ..ingestion.ingest_refined_flow import ingest_refined_file  # type: ignore
        except ImportError:  # pragma: no cover - fallback for direct execution
            from app.ingestion.ingest_refined_flow import ingest_refined_file  # type: ignore
        
        try:
            ingest_stats = ingest_refined_file(str(output_path), resolved_flow_name)
        except Exception as e:
            ingest_error = f"Vector DB ingestion failed: {str(e)}"
            print(f"[WARNING] {ingest_error}")

    return {
        "refined_path": str(output_path),
        "flow_name": resolved_flow_name,
        "ingested": bool(ingest_stats),
        "ingest_stats": ingest_stats,
        "ingest_error": ingest_error,
        "original_url": original_url,
        "total_actions": total_actions,
        "refined_steps": refined_steps,
        "filtered_count": total_actions - refined_steps,
    }
