# Framework Refinement Implementation Plan

## Summary of Requirements

### 1. **No LLM During Recording**
- Recording should be pure data capture without any LLM processing
- LLM usage restricted to:
  - Converting recorder JSON to plain English preview
  - Processing user feedback on preview
  - Generating test scripts with user feedback

### 2. **Code Structure & Template**
- Follow `framework_repos/a4901d37d4e0` structure
- Use `create-invoice-payables.spec.ts` as the reference template
- Maintain same patterns: testSetup, Excel integration, namedStep()

### 3. **Page-Based File Organization**
- Create separate page/locator files per `pageTitle`
- Example: `pageTitle: "Sign in to your account"` → `sign-in.page.ts` + `sign-in.ts` (locators)
- **Scan repository first** to find existing files
- **If exists**: Append content to existing files
- **If not exists**: Create new files

### 4. **Enhanced Locator Generation**
- Combine multiple factors: Playwright element + XPath/CSS
- XPath should include multiple attributes:
  - `//p[@class='activityTxt' and text()='View Assignments']`
  - Combine class, text, id, role, etc.

### 5. **Smart Login/Home Page Detection**
- Compare recorder's `startUrl` with existing login/home URLs
- **If match**: Reuse existing login.page.ts / home.page.ts
- **If different**: Create new page files

---

## Implementation Changes Required

### Change 1: Update LLM Script Prompt to Use Page Titles

**File**: `app/agentic_script_agent.py` (line ~336-450)

**Current Issue**: The script prompt doesn't consider page titles for file organization.

**Required Changes**:
```python
# In script_prompt template, add instructions:
"""
CRITICAL: PAGE-BASED FILE ORGANIZATION

Analyze the recorder steps and group by 'pageTitle':
- Extract unique pageTitles from the flow
- Create one locator file and one page file per pageTitle
- Filename convention: slugify(pageTitle) → e.g., "sign-in.ts", "sign-in.page.ts"

Example flow:
Steps 1-5: pageTitle="Sign in to your account" → files: locators/sign-in.ts, pages/SignInPage.ts
Steps 6-10: pageTitle="Home" → files: locators/home.ts, pages/HomePage.ts
Steps 11-20: pageTitle="Create Invoice" → files: locators/create-invoice.ts, pages/CreateInvoicePage.ts

REPOSITORY SCAN REQUIREMENT:
Before generating files, scan the framework repository:
1. List all existing .ts files in locators/ and pages/ directories
2. For each unique pageTitle in the flow:
   - Check if corresponding locator file exists (e.g., locators/sign-in.ts)
   - Check if corresponding page file exists (e.g., pages/SignInPage.ts)
   - If EXISTS: Return content to APPEND to existing file (add new locators/methods)
   - If NOT EXISTS: Generate complete new file

LOGIN/HOME PAGE DETECTION:
1. Extract startUrl from recorder metadata
2. Check existing login.page.ts and home.page.ts for their URLs
3. Compare URLs (ignore query params, compare base URL + path)
4. If startUrl matches login page URL → Reuse login.page.ts, don't create new
5. If startUrl matches home page URL → Reuse home.page.ts, don't create new
6. If different → Create new page file with appropriate name

ENHANCED LOCATOR GENERATION:
For each element, generate XPath combining multiple attributes:
- Prefer: //tag[@attr1='value1' and @attr2='value2' and text()='text']
- Include: id, class, role, name, text content
- Example: //button[@id='submit' and @class='btn primary' and text()='Submit']
- Example: //input[@type='email' and @placeholder='Enter email' and @aria-label='Email address']

Fallback priority:
1. Playwright getByRole/getByLabel/getByText (highest priority)
2. Multi-attribute XPath (combining 2+ attributes)
3. Single-attribute XPath
4. CSS selector (lowest priority)

Store ALL locator options in the locators file for resilience.
"""
```

### Change 2: Add Page Title Extraction to Context

**File**: `app/agentic_script_agent.py` - `gather_context()` method

**Add**:
```python
def gather_context(self, scenario: str) -> Dict[str, Any]:
    # ... existing code ...
    
    # Extract page titles from vector steps for file organization
    page_titles = set()
    page_url_map = {}  # Map page title to URL for login/home detection
    
    for step in vector_steps:
        page_title = step.get('pageTitle') or step.get('page_title')
        if page_title:
            page_titles.add(page_title)
            page_url = step.get('pageUrl') or step.get('page_url')
            if page_url:
                page_url_map[page_title] = page_url
    
    return {
        'enriched_steps': enriched_text,
        'existing_script': existing_script,
        'existing_excerpt': existing_excerpt,
        'scaffold_snippet': scaffold_snippet,
        'vector_steps': vector_steps,
        'vector_flow_name': vector_flow_name,
        'vector_flow_slug': vector_flow_slug,
        'page_titles': list(page_titles),  # Unique page titles
        'page_url_map': page_url_map,  # For URL comparison
        'start_url': vector_steps[0].get('original_url') if vector_steps else '',
    }
```

### Change 3: Enhance Deterministic Payload to Support Multi-Page Generation

**File**: `app/agentic_script_agent.py` - `_build_deterministic_payload()` method (line ~1399)

**Current Issue**: Generates single locator/page file for entire flow.

**Required Logic**:
```python
def _build_deterministic_payload(
    self,
    scenario: str,
    framework: FrameworkProfile,
    vector_steps: List[Dict[str, Any]],
    keep_signatures: Optional[Set[str]] = None,
) -> Dict[str, List[Dict[str, str]]]:
    
    # Group steps by pageTitle
    page_groups = self._group_steps_by_page_title(vector_steps)
    
    # Scan repository for existing page files
    existing_pages = self._scan_existing_pages(framework)
    existing_locators = self._scan_existing_locators(framework)
    
    # Detect login/home page URLs
    start_url = vector_steps[0].get('original_url') if vector_steps else ''
    login_url, home_url = self._get_login_home_urls(framework)
    
    all_locators = []
    all_pages = []
    all_tests = []
    
    for page_title, steps in page_groups.items():
        # Check if this is login/home page
        page_url = steps[0].get('pageUrl', '')
        if self._urls_match(page_url, login_url):
            # Reuse login page, don't generate new
            continue
        if self._urls_match(page_url, home_url):
            # Reuse home page, don't generate new
            continue
        
        # Generate file names from page title
        slug = _slugify(page_title)
        locator_filename = f"{slug}.ts"
        page_filename = f"{_to_camel_case(slug).capitalize()}Page.ts"
        
        # Check if files exist
        locator_path = framework.locators_dir / locator_filename
        page_path = framework.pages_dir / page_filename
        
        if locator_path.exists():
            # Append to existing locator file
            locator_content = self._generate_locators_append(locator_path, steps)
        else:
            # Create new locator file
            locator_content = self._generate_locators_new(slug, steps)
        
        if page_path.exists():
            # Append to existing page file
            page_content = self._generate_page_append(page_path, steps)
        else:
            # Create new page file
            page_content = self._generate_page_new(slug, page_title, steps, framework)
        
        all_locators.append({'path': str(locator_path.relative_to(framework.root)), 'content': locator_content})
        all_pages.append({'path': str(page_path.relative_to(framework.root)), 'content': page_content})
    
    # Generate single test file that uses all page objects
    test_content = self._generate_test_file(scenario, page_groups, framework, all_pages)
    all_tests.append({'path': f'tests/{_slugify(scenario)}.spec.ts', 'content': test_content})
    
    return {
        'locators': all_locators,
        'pages': all_pages,
        'tests': all_tests,
        'testDataMapping': self._generate_test_data_mapping(vector_steps),
    }
```

### Change 4: Implement Enhanced Locator Generation

**New Method**: `_generate_enhanced_xpath()`

```python
def _generate_enhanced_xpath(self, element: Dict[str, Any]) -> str:
    """Generate XPath combining multiple attributes for resilience."""
    html = element.get('html', '')
    selector = element.get('selector', {})
    
    # Extract attributes from HTML
    attributes = {}
    
    # Parse common attributes
    import re
    if '@id=' in html or 'id="' in html:
        id_match = re.search(r'id=["\']([^"\']+)["\']', html)
        if id_match:
            attributes['id'] = id_match.group(1)
    
    if 'class="' in html:
        class_match = re.search(r'class=["\']([^"\']+)["\']', html)
        if class_match:
            attributes['class'] = class_match.group(1)
    
    if 'role="' in html or 'aria-label="' in html:
        role_match = re.search(r'(?:role|aria-label)=["\']([^"\']+)["\']', html)
        if role_match:
            attributes['role'] = role_match.group(1)
    
    # Extract tag name
    tag_match = re.search(r'<(\w+)', html)
    tag = tag_match.group(1) if tag_match else '*'
    
    # Get visible text
    visible_text = element.get('visibleText', '').strip()
    
    # Build multi-attribute XPath
    conditions = []
    if 'id' in attributes:
        conditions.append(f"@id='{attributes['id']}'")
    if 'class' in attributes:
        # Use contains for class to handle multiple classes
        conditions.append(f"contains(@class, '{attributes['class'].split()[0]}')")
    if 'role' in attributes:
        conditions.append(f"@aria-label='{attributes['role']}'")
    if visible_text and len(visible_text) < 50:  # Only include short text
        conditions.append(f"text()='{visible_text}'")
    
    if conditions:
        xpath = f"//{tag}[{' and '.join(conditions)}]"
    else:
        # Fallback to simple xpath
        xpath = selector.get('xpath', f"//*")
    
    return xpath
```

### Change 5: Update Script Prompt to Include Page Organization

**Add to script_prompt template**:

```python
self.script_prompt = PromptTemplate(
    input_variables=[
        "scenario",
        "accepted_preview",
        "framework_summary",
        "page_titles",  # NEW
        "page_groups",  # NEW
        "existing_files",  # NEW
        "start_url",  # NEW
        "locators_snippet",
        "pages_snippet",
        "tests_snippet",
        "slug",
    ],
    template=(
        # ... existing prompt ...
        
        "PAGE-BASED FILE ORGANIZATION:\n"
        "The flow spans multiple pages with these titles: {page_titles}\n"
        "Existing files in repository: {existing_files}\n"
        "Start URL: {start_url}\n\n"
        
        "For each page title:\n"
        "1. Create locators/<page-slug>.ts with all locators for that page\n"
        "2. Create pages/<PageName>Page.ts with Page Object for that page\n"
        "3. If file already exists, APPEND new locators/methods instead of overwriting\n"
        "4. Check if start_url matches existing login.page.ts or home.page.ts URLs\n"
        "5. Reuse existing login/home pages if URLs match\n\n"
        
        "ENHANCED LOCATOR RULES:\n"
        "Generate multi-attribute XPath for each element:\n"
        "- Combine 2+ attributes when available\n"
        "- Example: //button[@id='submit' and @class='btn-primary' and text()='Submit']\n"
        "- Include: id, class, role, aria-label, text content\n"
        "- Store both Playwright selector AND enhanced XPath in locators file\n\n"
    )
)
```

---

## Files to Modify

### Primary Files:
1. **`app/agentic_script_agent.py`** (Major changes)
   - Update `gather_context()` to extract page titles
   - Modify `_build_deterministic_payload()` for multi-page generation
   - Add `_group_steps_by_page_title()`
   - Add `_scan_existing_pages()` and `_scan_existing_locators()`
   - Add `_get_login_home_urls()` and `_urls_match()`
   - Add `_generate_enhanced_xpath()`
   - Add `_generate_locators_append()` and `_generate_page_append()`
   - Update `script_prompt` template

2. **`app/recorder/recorder_auto_ingest.py`** (Minor verification)
   - Ensure no LLM calls during recording
   - Verify pageTitle is captured correctly

3. **`app/api/routers/agentic.py`** (Minor)
   - Ensure payload response includes all page-based files

### New Helper Methods Needed:

```python
def _group_steps_by_page_title(steps: List[Dict]) -> Dict[str, List[Dict]]:
    """Group steps by their pageTitle."""
    groups = {}
    for step in steps:
        title = step.get('pageTitle', 'UnknownPage')
        if title not in groups:
            groups[title] = []
        groups[title].append(step)
    return groups

def _urls_match(url1: str, url2: str) -> bool:
    """Compare two URLs ignoring query params and fragments."""
    from urllib.parse import urlparse
    p1 = urlparse(url1)
    p2 = urlparse(url2)
    return (p1.scheme == p2.scheme and 
            p1.netloc == p2.netloc and 
            p1.path == p2.path)

def _scan_existing_pages(framework: FrameworkProfile) -> List[str]:
    """Return list of existing page file names."""
    if not framework.pages_dir or not framework.pages_dir.exists():
        return []
    return [f.name for f in framework.pages_dir.glob('*.ts')]

def _scan_existing_locators(framework: FrameworkProfile) -> List[str]:
    """Return list of existing locator file names."""
    if not framework.locators_dir or not framework.locators_dir.exists():
        return []
    return [f.name for f in framework.locators_dir.glob('*.ts')]
```

---

## Testing Plan

1. **Test Page Title Extraction**:
   - Record flow with multiple page titles (e.g., login → home → invoice creation)
   - Verify each page title generates separate files

2. **Test Existing File Detection**:
   - Manually create sign-in.page.ts
   - Record flow with "Sign in to your account" page
   - Verify generator appends instead of overwrites

3. **Test Login/Home Reuse**:
   - Record flow starting from login URL
   - Verify login.page.ts is reused, not recreated

4. **Test Enhanced XPath**:
   - Inspect generated locators
   - Verify XPath includes multiple attributes

5. **Test User Feedback Loop**:
   - Generate preview
   - Modify preview steps
   - Generate script
   - Verify script reflects user changes

---

## Priority Order

**Phase 1** (Critical - Do First):
1. Remove any remaining LLM calls from recording
2. Add page title extraction to context gathering
3. Implement `_group_steps_by_page_title()`

**Phase 2** (High Priority):
4. Implement multi-page file generation in `_build_deterministic_payload()`
5. Add repository scanning for existing files
6. Implement append logic for existing files

**Phase 3** (Medium Priority):
7. Implement enhanced XPath generation
8. Add login/home URL comparison
9. Update script prompt with new instructions

**Phase 4** (Polish):
10. Test all scenarios
11. Refine prompts based on results
12. Document new file organization patterns

---

## Expected Outcome

After implementation:

1. **Recording**: Pure data capture, no LLM delays
2. **Preview**: LLM converts JSON to readable steps
3. **User Feedback**: Incorporated into final script generation
4. **File Structure**:
   ```
   framework_repos/a4901d37d4e0/
   ├── locators/
   │   ├── sign-in.ts          (pageTitle: "Sign in to your account")
   │   ├── home.ts             (pageTitle: "Home")
   │   └── create-invoice.ts   (pageTitle: "Create Invoice")
   ├── pages/
   │   ├── SignInPage.ts
   │   ├── HomePage.ts
   │   └── CreateInvoicePage.ts
   └── tests/
       └── invoice-flow.spec.ts (imports all pages)
   ```
5. **Locators**: Multi-attribute XPath for resilience
6. **Smart Reuse**: Existing login/home pages reused when URLs match
