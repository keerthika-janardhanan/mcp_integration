import re
import json
from typing import List, Dict, Any, Optional


def _extract_string_arg(s: str) -> str | None:
    m = re.search(r"\(\s*['\"](.*?)['\"]", s)
    return m.group(1) if m else None


def _extract_role_and_name(s: str) -> tuple[str | None, str | None]:
    role = None
    name = None
    m_role = re.search(r"getByRole\(\s*['\"](.*?)['\"]", s)
    if m_role:
        role = m_role.group(1)
    m_name = re.search(r"name\s*:\s*['\"](.*?)['\"]", s)
    if m_name:
        name = m_name.group(1)
    return role, name


def _escape(text: str) -> str:
    # Simple XPath string literal escape that handles quotes by using concat if needed
    if "'" not in text:
        return f"'{text}'"
    if '"' not in text:
        return f'"{text}"'
    parts = []
    for part in text.split("'"):
        parts.append(f"'{part}'")
        parts.append('"' + "'" + '"')
    parts.pop()  # remove last added quote concat
    return "concat(" + ", ".join(parts) + ")"


def generate_xpath_candidates(selector_expr: str) -> List[str]:
    """
    Convert a Playwright selector expression like `page.getByText('Save')` or
    `page.getByRole('button', { name: 'Save' })` into a set of resilient XPath
    candidates including parent/sibling anchored variants suitable for Oracle
    Fusion UIs that change ids across patches.
    """
    s = selector_expr
    cands: list[str] = []

    # 1) Direct getByText
    if "getByText(" in s:
        text = _extract_string_arg(s)
        if text:
            esc = _escape(text.strip())
            cands.append(f"//*[normalize-space(.)={esc}]")
            # label -> input sibling pattern
            cands.append(
                f"//label[normalize-space(.)={esc}]/following::*[self::input or self::textarea or self::select][1]"
            )
            # parent anchored descendant
            cands.append(
                f"//*[normalize-space(.)={esc}]/ancestor::*[self::section or self::div or self::td or self::li][1]//*[self::input or self::button or self::a or self::span]"
            )

    # 2) getByRole with name
    elif "getByRole(" in s:
        role, name = _extract_role_and_name(s)
        role = (role or "").lower()
        esc_name = _escape(name.strip()) if name else None

        if role == "button":
            if esc_name:
                cands.append(f"//button[normalize-space(.)={esc_name}]")
                cands.append(f"//*[@role='button' and normalize-space(.)={esc_name}]")
                cands.append(
                    f"//span[normalize-space(.)={esc_name}]/ancestor::*[self::button or self::a][1]"
                )
            else:
                cands.append("//button | //*[@role='button']")

        elif role in {"link", "menuitem", "tab"}:
            if esc_name:
                cands.append(f"//a[normalize-space(.)={esc_name}] | //*[@role='{role}' and normalize-space(.)={esc_name}]")
            else:
                cands.append(f"//*[@role='{role}']")

        elif role in {"textbox", "combobox", "searchbox", "spinbutton"}:
            # try by associated label name first if provided
            if esc_name:
                cands.append(
                    f"//label[normalize-space(.)={esc_name}]/following::*[self::input or self::textarea or self::select][1]"
                )
            # generic role-based fallback
            cands.append(f"//*[@role='{role}']")

        else:
            if esc_name:
                cands.append(f"//*[@role='{role}' and normalize-space(.)={esc_name}]")
            else:
                cands.append(f"//*[@role='{role}']")

    # 3) getByLabel
    elif "getByLabel(" in s:
        label = _extract_string_arg(s)
        if label:
            esc = _escape(label.strip())
            cands.append(
                f"//label[normalize-space(.)={esc}]/following::*[self::input or self::textarea or self::select][1]"
            )
            cands.append(
                f"//*[@aria-label and normalize-space(@aria-label)={esc}] | //*[@placeholder and normalize-space(@placeholder)={esc}]"
            )

    # 4) getByTitle
    elif "getByTitle(" in s:
        title = _extract_string_arg(s)
        if title:
            esc = _escape(title.strip())
            cands.append(f"//*[@title and normalize-space(@title)={esc}]")

    # 5) locator('xpath=...') or locator('css=...')
    elif "locator(" in s:
        m = re.search(r"locator\(\s*['\"](.*?)['\"]\s*\)", s)
        if m:
            inner = m.group(1)
            if inner.startswith("xpath="):
                cands.append(inner.replace("xpath=", ""))
            elif inner.startswith("oracle-xpath="):
                cands.append(inner.replace("oracle-xpath=", ""))
            elif inner.startswith("text="):
                txt = inner.split("=", 1)[1]
                cands.append(f"//*[contains(normalize-space(.), {_escape(txt)})]")
            elif inner.startswith("css="):
                # No DOM to translate robustly; keep a generic attribute-based fallback
                cands.append("//*[@id or @class or @data-testid][1]")

    # 6) Final generic fallbacks leveraging Oracle Fusion id patterns
    # If nothing captured above, try a few robust patterns
    if not cands:
        cands.append("//*[@data-testid or @aria-label or @title]")
        cands.append("//*[contains(@id, ':')]")  # Oracle ADF-style ids often contain ':'

    # Deduplicate while preserving order
    seen = set()
    uniq: list[str] = []
    for x in cands:
        if x not in seen:
            uniq.append(x)
            seen.add(x)
    return uniq


def to_union_xpath(candidates: List[str]) -> str:
    """Join candidates using XPath union for resilient matching."""
    if not candidates:
        return "//unknown"
    return " | ".join(candidates)


def generate_locator_with_llm(
    element_data: Dict[str, Any],
    visible_text: str = "",
    page_context: str = ""
) -> Dict[str, Any]:
    """
    Use Copilot LLM to generate the best locator strategy based on:
    - CSS selectors
    - XPath
    - Playwright locators (getByText, getByRole, getByLabel)
    - Visible text
    - Page context
    
    Returns a dict with:
    - recommended: The best locator strategy
    - alternatives: List of fallback locators
    - reasoning: Why this locator was chosen
    """
    try:
        from ..core.llm_client_copilot import CopilotClient
        use_copilot = True
    except ImportError:
        use_copilot = False
    
    # Extract available selectors
    selectors = element_data.get("selector", {})
    css_selector = selectors.get("css", "")
    xpath_selector = selectors.get("xpath", "")
    playwright_selectors = selectors.get("playwright", {})
    html = element_data.get("html", "")
    
    # Build context for LLM
    prompt = f"""Analyze this web element and recommend the BEST Playwright locator strategy.

Element Information:
- Visible Text: {visible_text or 'N/A'}
- HTML: {html[:500] if html else 'N/A'}
- CSS Selector: {css_selector or 'N/A'}
- XPath: {xpath_selector or 'N/A'}

Available Playwright Selectors:
{json.dumps(playwright_selectors, indent=2) if playwright_selectors else 'None'}

Page Context: {page_context or 'General web application'}

Requirements:
1. Prioritize in this order:
   - getByRole (most semantic and accessible)
   - getByLabel (for form inputs)
   - getByText (for buttons/links with unique text)
   - getByTestId (if data-testid exists)
   - CSS selector (if stable and not auto-generated)
   - XPath (only as last resort, make it resilient)

2. For Oracle Fusion apps specifically:
   - Avoid dynamic IDs that contain random strings
   - Use text-based locators when possible
   - Create resilient XPath with normalize-space and ancestor patterns

3. Return ONLY a JSON object with:
{{
  "recommended": "page.getByRole('button', {{ name: 'Save' }})",
  "alternatives": ["page.getByText('Save')", "//button[text()='Save']"],
  "reasoning": "Brief explanation why this is the best choice"
}}"""

    if use_copilot:
        try:
            client = CopilotClient()
            response = client.invoke(prompt)
            
            # Get content from response
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            # Try to extract JSON from response
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                result = json.loads(json_match.group(0))
                return result
        except Exception as e:
            print(f"[LLM Locator] Failed to generate with LLM: {e}")
    
    # Fallback: Use rule-based prioritization
    alternatives = []
    
    # Priority 1: Playwright role-based
    if playwright_selectors.get("byRole"):
        recommended = f"page.{playwright_selectors['byRole']}"
        if playwright_selectors.get("byText"):
            alternatives.append(f"page.{playwright_selectors['byText']}")
        if playwright_selectors.get("byLabel"):
            alternatives.append(f"page.{playwright_selectors['byLabel']}")
        return {
            "recommended": recommended,
            "alternatives": alternatives,
            "reasoning": "Role-based locator is most semantic and accessible"
        }
    
    # Priority 2: Label-based for inputs
    if playwright_selectors.get("byLabel"):
        recommended = f"page.{playwright_selectors['byLabel']}"
        if playwright_selectors.get("byPlaceholder"):
            alternatives.append(f"page.{playwright_selectors['byPlaceholder']}")
        return {
            "recommended": recommended,
            "alternatives": alternatives,
            "reasoning": "Label-based locator is stable for form inputs"
        }
    
    # Priority 3: Text-based
    if playwright_selectors.get("byText") and visible_text and len(visible_text) > 2:
        recommended = f"page.{playwright_selectors['byText']}"
        if css_selector and not re.search(r'[a-f0-9]{8,}|pt\d+|_\d+', css_selector):
            alternatives.append(f"page.locator('{css_selector}')")
        return {
            "recommended": recommended,
            "alternatives": alternatives,
            "reasoning": "Text-based locator is readable and stable if text is unique"
        }
    
    # Priority 4: TestId
    if playwright_selectors.get("byTestId"):
        return {
            "recommended": f"page.{playwright_selectors['byTestId']}",
            "alternatives": [],
            "reasoning": "Test ID is explicitly designed for testing"
        }
    
    # Priority 5: CSS (if stable)
    if css_selector and not re.search(r'[a-f0-9]{8,}|pt\d+|_\d+', css_selector):
        xpath_candidates = generate_xpath_candidates(css_selector)
        return {
            "recommended": f"page.locator('{css_selector}')",
            "alternatives": [f"page.locator('xpath={xpath_candidates[0]}')" if xpath_candidates else xpath_selector],
            "reasoning": "CSS selector appears stable (no auto-generated IDs)"
        }
    
    # Priority 6: Resilient XPath
    xpath_candidates = generate_xpath_candidates(xpath_selector or css_selector)
    union_xpath = to_union_xpath(xpath_candidates)
    
    return {
        "recommended": f"page.locator('xpath={union_xpath}')",
        "alternatives": xpath_candidates[1:3] if len(xpath_candidates) > 1 else [],
        "reasoning": "Generated resilient XPath with multiple fallback patterns"
    }
