# How LLM Determines Wait Times and Dynamic Selectors

## Overview

The LLM doesn't "guess" - it analyzes **recorded metadata** from user actions to intelligently determine:
1. **When to add wait conditions**
2. **What type of wait to use**
3. **How to select dynamic elements (tables, dropdowns)**
4. **Whether to use name-based or index-based selection**

## Data Flow: From Recording to Intelligent Code

### Step 1: Recorder Captures Rich Metadata

When you interact with the application, the recorder captures:

```json
{
  "step": 5,
  "action": "click",
  "navigation": "Click on supplier row in search results table",
  "visibleText": "ACME Corporation",  // ← CRITICAL: What user SAW
  "locators": {
    "playwright": "getByRole('row')",
    "css": "table tbody tr:nth-child(3)",
    "xpath": "//table//tr[contains(text(), 'ACME')]"
  },
  "data": "",
  "expected": "Opens supplier details"
}
```

### Step 2: System Analyzes Step Metadata

The `_prepare_step_details()` function enriches each step:

```python
enhanced_step = {
    'step_number': 5,
    'action': 'click',
    'navigation': 'Click on supplier row in search results table',
    'visible_text': 'ACME Corporation',  # What user clicked
    
    # INFERRED METADATA:
    'element_type': 'table',  # Detected from 'table' in navigation
    'is_dynamic': True,       # Detected from 'search results' keywords
    
    'wait_requirements': {
        'required': True,
        'type': 'element_visible',
        'reason': 'Previous step "Search supplier" triggers data loading',
        'duration_ms': None
    },
    
    'selection_method': {
        'method': 'by-text',
        'criteria': 'ACME Corporation',  # From visibleText
        'reason': "Table row clicked with visible text 'ACME Corporation' - use flexible text-based selector"
    },
    
    'reasoning': "Table interaction with visible text 'ACME Corporation' - generate flexible row selector | Dynamic element - add explicit wait"
}
```

### Step 3: LLM Receives Explicit Instructions

The prompt includes:

```
## HOW TO INTERPRET STEP METADATA

### Understanding 'visibleText' Field
- This is the text the user SAW when they clicked
- For tables: This is the row content (e.g., "ACME Corporation")
- ACTION: Use this for flexible selectors: filter({ hasText: 'ACME Corporation' })

### Understanding 'wait_requirements' Field
- required: true = MUST add wait condition
- type: 'element_visible' = Add await element.waitFor({ state: 'visible' })
- reason: "Previous step triggers data loading"

### Understanding 'selection_method' Field
- method: 'by-text'
- criteria: 'ACME Corporation'
- Use: page.getByRole('row').filter({ hasText: 'ACME Corporation' })
```

### Step 4: LLM Generates Intelligent Code

Based on the metadata, LLM generates:

```typescript
// Locators file
get supplierRow(): Locator {
  // Using visibleText for flexible selection
  return this.page.getByRole('row').filter({ 
    hasText: 'ACME Corporation' 
  });
}

// Also provide by-index for edge cases
supplierRowByIndex(index: number): Locator {
  return this.page.locator(`table tbody tr:nth-child(${index})`);
}

// Page object file
async selectSupplierRow(supplierName: string): Promise<void> {
  // Wait for table to be visible (from wait_requirements)
  const table = this.page.locator('table');
  await table.waitFor({ state: 'visible' });
  
  // Select by name (from selection_method: 'by-text')
  const row = this.page.getByRole('row').filter({ 
    hasText: supplierName 
  });
  await row.click();
  
  // Wait for dynamic content to load (from is_dynamic: true)
  await this.waitForDynamicContent();
}
```

## Detailed Analysis Examples

### Example 1: Table Row Selection by Name

**Recorded Data:**
```json
{
  "step": 3,
  "action": "click",
  "navigation": "Select row with supplier name from table",
  "visibleText": "ABC Industries",
  "locators": {
    "playwright": "getByRole('row')",
    "css": "table tr:nth-child(2)"
  }
}
```

**System Analysis:**
```python
# _infer_element_type() detects:
element_type = 'table'  # Because 'table' in navigation

# _infer_selection_method() determines:
selection_method = {
    'method': 'by-text',
    'criteria': 'ABC Industries',
    'reason': "Table row with visible text 'ABC Industries' - use flexible selector"
}

# _infer_wait_requirements() decides:
wait_requirements = {
    'required': True,
    'type': 'element_visible',
    'reason': 'Dynamic table needs to be visible before interaction'
}
```

**Generated Code:**
```typescript
// Flexible - works with ANY row containing this text
async selectSupplierByName(supplierName: string): Promise<void> {
  await this.page.locator('table').waitFor({ state: 'visible' });
  const row = this.page.getByRole('row').filter({ hasText: supplierName });
  await row.click();
}

// Test uses data-driven value
await page.selectSupplierByName(testData.supplierName); // Not hardcoded!
```

### Example 2: Dropdown Selection by Label

**Recorded Data:**
```json
{
  "step": 2,
  "action": "select",
  "navigation": "Select country from dropdown",
  "visibleText": "United States",
  "locators": {
    "playwright": "getByLabel('Country')",
    "css": "#country-select"
  },
  "data": "United States"
}
```

**System Analysis:**
```python
element_type = 'dropdown'  # From action='select' and 'dropdown' in navigation

selection_method = {
    'method': 'by-text',
    'criteria': 'United States',
    'reason': "Dropdown selection by visible label 'United States'"
}

wait_requirements = {
    'required': True,
    'type': 'element_visible',
    'reason': 'Dropdown options may load dynamically'
}
```

**Generated Code:**
```typescript
async selectCountry(country: string): Promise<void> {
  const dropdown = this.locators.countryDropdown;
  await dropdown.waitFor({ state: 'visible' });
  
  // Use label, not value attribute
  await dropdown.selectOption({ label: country });
}
```

### Example 3: Search with Loading Wait

**Recorded Data:**
```json
[
  {
    "step": 1,
    "action": "fill",
    "navigation": "Enter search term",
    "visibleText": "",
    "data": "ACME",
    "locators": { "playwright": "getByPlaceholder('Search...')" }
  },
  {
    "step": 2,
    "action": "click",
    "navigation": "Click search button",
    "visibleText": "Search"
  },
  {
    "step": 3,
    "action": "click",
    "navigation": "Select result from search results table",
    "visibleText": "ACME Corporation"
  }
]
```

**System Analysis for Step 3:**
```python
# _infer_wait_requirements() checks PREVIOUS step
prev_step = steps[1]  # Search button click
prev_navigation = "Click search button"

wait_requirements = {
    'required': True,
    'type': 'loading_hidden',
    'reason': "Previous step 'Click search button' likely triggers data loading"
}

element_type = 'table'
is_dynamic = True  # 'search results' is dynamic keyword

selection_method = {
    'method': 'by-text',
    'criteria': 'ACME Corporation',
    'reason': "Selecting from search results by text"
}
```

**Generated Code:**
```typescript
async searchAndSelectSupplier(searchTerm: string, supplierName: string): Promise<void> {
  // Step 1: Fill search
  await this.locators.searchInput.fill(searchTerm);
  
  // Step 2: Click search
  await this.locators.searchButton.click();
  
  // Step 3: Wait for loading to complete (from wait_requirements)
  await this.waitForDynamicContent();
  
  // Select result by name (from selection_method: by-text)
  const resultRow = this.page.getByRole('row').filter({ 
    hasText: supplierName 
  });
  await resultRow.waitFor({ state: 'visible' });
  await resultRow.click();
}
```

## Wait Detection Rules

### Rule 1: Navigation Actions
```python
if action in ['navigate', 'goto'] or 'navigate' in navigation:
    wait_type = 'networkidle'
    reason = "Page navigation requires network to settle"
```

**Example:**
```typescript
async navigate(url: string) {
  await this.page.goto(url);
  await this.page.waitForLoadState('networkidle'); // ← Auto-added
}
```

### Rule 2: Previous Step Triggers Loading
```python
if prev_step.action in ['search', 'filter', 'submit', 'click']:
    wait_type = 'loading_hidden'
    reason = f"Previous step '{prev_navigation}' triggers loading"
```

**Example:**
```typescript
async clickSearchButton() {
  await this.locators.searchButton.click();
}

async selectResult() {
  // Wait added because previous step was search
  await this.page.locator('.loading').waitFor({ state: 'hidden' });
  await this.locators.resultRow.click();
}
```

### Rule 3: Dynamic Elements (Tables, Results)
```python
if 'table' in navigation or 'row' in navigation or 'result' in navigation:
    wait_type = 'element_visible'
    reason = "Dynamic table/results need to be visible"
```

**Example:**
```typescript
async selectTableRow(rowText: string) {
  const table = this.page.locator('table');
  await table.waitFor({ state: 'visible' }); // ← Auto-added
  
  const row = table.locator('tr').filter({ hasText: rowText });
  await row.click();
}
```

### Rule 4: Form Submission
```python
if 'submit' in navigation or 'save' in navigation:
    wait_type = 'networkidle'
    reason = "Form submission needs server response wait"
```

**Example:**
```typescript
async submitForm() {
  await this.locators.submitButton.click();
  await this.page.waitForLoadState('networkidle'); // ← Auto-added
}
```

## Selection Method Detection

### Detection Logic

```python
def _infer_selection_method(step):
    element_type = _infer_element_type(step)
    visible_text = step.get('visibleText', '')
    
    # Table with visible text → by-text
    if element_type == 'table' and visible_text:
        return {
            'method': 'by-text',
            'criteria': visible_text,
            'reason': f"Use text '{visible_text}' for flexible table selection"
        }
    
    # Table without visible text → by-index (warn)
    elif element_type == 'table' and not visible_text:
        return {
            'method': 'by-index',
            'criteria': 'first',
            'reason': "No visible text - using index (brittle)"
        }
    
    # Dropdown → by-label
    elif element_type == 'dropdown':
        return {
            'method': 'by-text',
            'criteria': visible_text or step.get('data'),
            'reason': "Use label for dropdown selection"
        }
```

### Generated Patterns

**Pattern 1: Flexible Table Selection**
```typescript
// Generated locator with parameter
tableRowByText(text: string): Locator {
  return this.page.getByRole('row').filter({ hasText: text });
}

// Generated method
async selectSupplier(supplierName: string) {
  const row = this.locators.tableRowByText(supplierName);
  await row.click();
}

// Test uses data
await page.selectSupplier(testData.supplierName);
```

**Pattern 2: Dropdown by Label**
```typescript
async selectCountry(countryName: string) {
  await this.locators.countryDropdown.selectOption({ 
    label: countryName  // By label, not value
  });
}
```

**Pattern 3: Index-based (Fallback)**
```typescript
// Only generated when visibleText not available
tableRowByIndex(index: number): Locator {
  return this.page.locator(`table tbody tr:nth-child(${index})`);
}

// With warning comment
async selectRowByIndex(index: number) {
  // WARNING: Index-based selection is brittle
  // Consider using selectRowByText() instead
  await this.locators.tableRowByIndex(index).click();
}
```

## Real-World Example: Complete Flow

### Recorded Steps (Raw)
```json
[
  {
    "step": 1,
    "action": "click",
    "navigation": "Click Suppliers menu",
    "visibleText": "Suppliers"
  },
  {
    "step": 2,
    "action": "fill",
    "navigation": "Enter supplier name in search",
    "data": "ACME"
  },
  {
    "step": 3,
    "action": "click",
    "navigation": "Click Search button",
    "visibleText": "Search"
  },
  {
    "step": 4,
    "action": "click",
    "navigation": "Select supplier from results table",
    "visibleText": "ACME Corporation"
  },
  {
    "step": 5,
    "action": "click",
    "navigation": "Click Edit button",
    "visibleText": "Edit"
  }
]
```

### Enhanced Steps (After Analysis)
```json
[
  {
    "step": 1,
    "element_type": "link",
    "wait_requirements": { "required": false },
    "selection_method": { "method": "by-text", "criteria": "Suppliers" }
  },
  {
    "step": 2,
    "element_type": "input",
    "wait_requirements": { "required": false }
  },
  {
    "step": 3,
    "element_type": "button",
    "wait_requirements": { 
      "required": true,
      "type": "networkidle",
      "reason": "Search button triggers data fetch"
    }
  },
  {
    "step": 4,
    "element_type": "table",
    "is_dynamic": true,
    "wait_requirements": {
      "required": true,
      "type": "loading_hidden",
      "reason": "Previous search triggers loading"
    },
    "selection_method": {
      "method": "by-text",
      "criteria": "ACME Corporation",
      "reason": "Table row with visible text - flexible selector"
    }
  },
  {
    "step": 5,
    "wait_requirements": {
      "required": true,
      "type": "element_visible",
      "reason": "Button may appear after row selection"
    }
  }
]
```

### Generated Code
```typescript
// Page Object
export class SupplierSearchPage extends BasePage {
  
  async navigateToSuppliers() {
    await this.page.getByText('Suppliers').click();
    // No wait needed - simple navigation
  }
  
  async searchSupplier(searchTerm: string) {
    await this.locators.searchInput.fill(searchTerm);
    await this.locators.searchButton.click();
    
    // Wait for search to complete
    await this.page.waitForLoadState('networkidle');
  }
  
  async selectSupplierByName(supplierName: string) {
    // Wait for loading indicator to hide
    await this.waitForDynamicContent();
    
    // Select by name (flexible!)
    const row = this.page.getByRole('row').filter({ 
      hasText: supplierName 
    });
    await row.waitFor({ state: 'visible' });
    await row.click();
  }
  
  async clickEdit() {
    const editButton = this.locators.editButton;
    await editButton.waitFor({ state: 'visible' });
    await editButton.click();
  }
}

// Test
test('Search and edit supplier', async () => {
  await page.navigateToSuppliers();
  await page.searchSupplier(testData.searchTerm);
  await page.selectSupplierByName(testData.supplierName); // Data-driven!
  await page.clickEdit();
});
```

## Key Takeaways

### 1. **visibleText is the Key**
- Captured by recorder during interaction
- Tells LLM EXACTLY what user clicked
- Enables flexible, text-based selectors

### 2. **Wait Detection is Context-Aware**
- Analyzes previous steps for triggers
- Detects keywords (search, filter, submit)
- Identifies dynamic elements (tables, results)

### 3. **Selection Method is Inferred**
- Table + visibleText = by-text selector
- Table without visibleText = warning + by-index fallback
- Dropdown = always by-label

### 4. **LLM Receives Explicit Instructions**
- Every step has detailed metadata
- Prompt explains HOW to interpret each field
- No guessing - clear rules

### 5. **Generated Code is Flexible**
- Parameters instead of hardcoded values
- Data-driven from test data JSON
- Works across different scenarios

---

**The Bottom Line**: The LLM doesn't "figure it out" - it follows explicit analysis provided by the system based on captured recorder metadata. The intelligence is in the **metadata enrichment**, not magic!
