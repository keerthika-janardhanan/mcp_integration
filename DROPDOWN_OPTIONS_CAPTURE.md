# Dropdown Options Capture - Data-Driven Testing

## Problem Solved

**Before**: Recorder only captured the ONE option the user selected during recording. Tests could only use that exact value.

**After**: Recorder captures ALL available options in the dropdown. Tests can select ANY option using test data.

## How It Works

### 1. Enhanced Recorder Captures All Options

When user interacts with a dropdown, the recorder now captures:

```json
{
  "step": 3,
  "action": "change",
  "navigation": "Select country from dropdown",
  "visibleText": "United States",
  "selectedValue": "United States",  // ← What user selected
  "dropdownOptions": [               // ← ALL available options
    { "value": "US", "text": "United States", "selected": true },
    { "value": "CA", "text": "Canada", "selected": false },
    { "value": "MX", "text": "Mexico", "selected": false },
    { "value": "UK", "text": "United Kingdom", "selected": false },
    { "value": "DE", "text": "Germany", "selected": false }
  ],
  "locators": {
    "playwright": "getByLabel('Country')",
    "css": "#country-select"
  }
}
```

### 2. System Analyzes Dropdown Metadata

```python
# _infer_selection_method() extracts:
selection_method = {
    'method': 'by-text',
    'criteria': 'United States',  # What was selected
    'available_options': [
        'United States',
        'Canada', 
        'Mexico',
        'United Kingdom',
        'Germany'
    ],  # ALL options
    'reason': "Dropdown with 5 options captured. Selected: 'United States'"
}
```

### 3. LLM Generates Flexible, Typed Code

#### Generated Locator (Basic)
```typescript
// locators/supplier.locators.ts
get countryDropdown(): Locator {
  return this.page.getByLabel('Country');
}
```

#### Generated Page Object (Type-Safe)
```typescript
// pages/supplier.page.ts
export class SupplierPage extends BasePage {
  
  /**
   * Select country from dropdown
   * Available options: United States, Canada, Mexico, United Kingdom, Germany
   */
  async selectCountry(
    country: 'United States' | 'Canada' | 'Mexico' | 'United Kingdom' | 'Germany'
  ): Promise<void> {
    // Validate option exists (optional but recommended)
    const validOptions = ['United States', 'Canada', 'Mexico', 'United Kingdom', 'Germany'];
    if (!validOptions.includes(country)) {
      throw new Error(`Invalid country: ${country}. Valid options: ${validOptions.join(', ')}`);
    }
    
    // Wait for dropdown to be ready
    const dropdown = this.locators.countryDropdown;
    await dropdown.waitFor({ state: 'visible' });
    
    // Select by label (visible text, not value attribute)
    await dropdown.selectOption({ label: country });
    
    // Optional: wait for any dependent fields to update
    await this.page.waitForTimeout(300);
  }
}
```

#### Generated Test (Data-Driven)
```typescript
// tests/supplier.spec.ts
import testData from '../data/supplier_data.json';

test('Create supplier with different countries', async () => {
  const page = new SupplierPage(testPage);
  
  await page.navigate(startUrl);
  await page.fillSupplierName(testData.supplierName);
  
  // Can select ANY captured option - not hardcoded!
  await page.selectCountry(testData.country);  // Type-safe!
  
  await page.submit();
});
```

#### Generated Test Data (Multiple Scenarios)
```json
{
  "flowName": "Create Supplier",
  "testData": [
    {
      "name": "US_supplier",
      "supplierName": "ACME Corp",
      "country": "United States"
    },
    {
      "name": "Canadian_supplier",
      "supplierName": "Maple Leaf Inc",
      "country": "Canada"
    },
    {
      "name": "Mexican_supplier",
      "supplierName": "Sol Industries",
      "country": "Mexico"
    }
  ],
  "fields": [
    {
      "fieldName": "country",
      "step": 3,
      "action": "select",
      "description": "Select country from dropdown",
      "sampleValue": "United States",
      "required": true,
      "dataType": "dropdown",
      "availableOptions": [
        "United States",
        "Canada",
        "Mexico",
        "United Kingdom",
        "Germany"
      ],
      "validationRules": {
        "enum": ["United States", "Canada", "Mexico", "United Kingdom", "Germany"]
      }
    }
  ]
}
```

## Benefits

### 1. **Type Safety**
```typescript
// TypeScript will catch errors at compile time
await page.selectCountry('France');  // ❌ Error: Not in union type
await page.selectCountry('Canada');  // ✅ Valid
```

### 2. **Data-Driven Testing**
```typescript
// Test with multiple data sets
for (const dataSet of testData.testData) {
  test(`Create supplier - ${dataSet.name}`, async () => {
    await page.selectCountry(dataSet.country);  // Different for each test
  });
}
```

### 3. **Self-Documenting Code**
```typescript
/**
 * Available options: United States, Canada, Mexico, United Kingdom, Germany
 */
async selectCountry(country: 'United States' | 'Canada' | ...) {
  // Developer knows exactly what options are valid
}
```

### 4. **Runtime Validation**
```typescript
// Optional validation catches invalid test data early
const validOptions = ['United States', 'Canada', 'Mexico', ...];
if (!validOptions.includes(country)) {
  throw new Error(`Invalid country: ${country}`);
}
```

### 5. **IDE Autocomplete**
```typescript
// IDE will show all valid options
await page.selectCountry('...')  
// Autocomplete suggests: United States, Canada, Mexico, etc.
```

## Example Scenarios

### Scenario 1: Multiple Dropdowns

**Recorded**:
```json
[
  {
    "step": 2,
    "action": "change",
    "dropdownOptions": [
      {"text": "United States", "selected": true},
      {"text": "Canada"},
      {"text": "Mexico"}
    ]
  },
  {
    "step": 3,
    "action": "change",
    "dropdownOptions": [
      {"text": "Alabama"},
      {"text": "California", "selected": true},
      {"text": "New York"}
    ]
  }
]
```

**Generated**:
```typescript
async selectCountry(country: 'United States' | 'Canada' | 'Mexico') { ... }
async selectState(state: 'Alabama' | 'California' | 'New York') { ... }

// Test
await page.selectCountry(testData.country);
await page.selectState(testData.state);
```

### Scenario 2: Dropdown Without Captured Options (Fallback)

**Recorded** (options not captured - maybe dynamic loading):
```json
{
  "step": 2,
  "action": "change",
  "visibleText": "Manager",
  "dropdownOptions": null  // ← Not captured
}
```

**Generated** (Flexible string type):
```typescript
async selectRole(role: string): Promise<void> {
  // No validation - options not known at generation time
  await this.locators.roleDropdown.selectOption({ label: role });
}
```

### Scenario 3: Dependent Dropdowns

**Recorded**:
```json
[
  {
    "step": 2,
    "action": "change",
    "navigation": "Select country",
    "dropdownOptions": [...]  // Countries
  },
  {
    "step": 3,
    "action": "change",
    "navigation": "Select state (changes based on country)",
    "dropdownOptions": [...]  // States for selected country
  }
]
```

**Generated** (With wait for dependent update):
```typescript
async selectCountry(country: 'US' | 'CA' | 'MX') {
  await this.locators.countryDropdown.selectOption({ label: country });
  
  // Wait for state dropdown to update with new options
  await this.page.waitForLoadState('networkidle');
  await this.page.waitForTimeout(500);  // Additional buffer
}

async selectState(state: string) {
  // State options change based on country, so accept any string
  await this.locators.stateDropdown.waitFor({ state: 'visible' });
  await this.locators.stateDropdown.selectOption({ label: state });
}
```

## Edge Cases Handled

### 1. **Options Load Dynamically**
If dropdown options load after page load (AJAX), recorder captures them when user interacts:
```javascript
// Recorder waits for user to click dropdown
// THEN captures all visible options
// Works even if options loaded via AJAX
```

### 2. **Large Dropdown (100+ Options)**
All options captured, but TypeScript union type may be verbose:
```typescript
// Option 1: Keep full union type (verbose but type-safe)
async select(option: 'Option1' | 'Option2' | ... | 'Option100') { }

// Option 2: Use string + validation (cleaner)
async select(option: string) {
  const validOptions = ['Option1', 'Option2', ..., 'Option100'];
  if (!validOptions.includes(option)) {
    throw new Error(`Invalid option: ${option}`);
  }
  // ...
}
```

### 3. **Multi-Select Dropdown**
Captures all available options plus which ones are selected:
```json
{
  "dropdownOptions": [
    {"text": "Admin", "selected": true},
    {"text": "User", "selected": true},
    {"text": "Guest", "selected": false}
  ]
}
```

**Generated**:
```typescript
async selectRoles(roles: Array<'Admin' | 'User' | 'Guest'>) {
  for (const role of roles) {
    await this.locators.rolesMultiSelect.selectOption({ label: role });
  }
}
```

## Comparison: Before vs After

### Before (Without Option Capture)
```typescript
// ❌ Only works with the value user selected during recording
async selectCountry() {
  await this.locators.countryDropdown.selectOption({ label: 'United States' });
}

// Test is NOT data-driven
test('Create supplier', async () => {
  await page.selectCountry();  // Always selects "United States"
});
```

### After (With Option Capture)
```typescript
// ✅ Works with ANY captured option
async selectCountry(country: 'United States' | 'Canada' | 'Mexico') {
  await this.locators.countryDropdown.selectOption({ label: country });
}

// Test IS data-driven
test('Create supplier', async () => {
  await page.selectCountry(testData.country);  // Can be any option!
});
```

## Implementation Details

### Recorder Enhancement (JavaScript Injection)
```javascript
// In capture() function
if (target.tagName === 'SELECT') {
  dropdownOptions = Array.from(target.options).map(opt => ({
    value: opt.value,
    text: opt.text,
    selected: opt.selected
  }));
  selectedValue = target.options[target.selectedIndex]?.text;
}
```

### System Analysis (Python)
```python
# _infer_selection_method()
if element_type == 'dropdown':
    dropdown_options = step.get('dropdownOptions', [])
    if dropdown_options:
        selection['available_options'] = [opt['text'] for opt in dropdown_options]
        # LLM will use this to generate union type
```

### LLM Prompt (Enhanced)
```
### Understanding 'dropdownOptions' Field
- Contains ALL available options from the dropdown
- Generate methods that accept ANY option, not just selectedValue
- Use TypeScript union types: 'Option1' | 'Option2' | 'Option3'
- This enables data-driven testing
```

## Testing Examples

### Test Data Variations
```json
{
  "testData": [
    {"name": "test_us", "country": "United States"},
    {"name": "test_canada", "country": "Canada"},
    {"name": "test_mexico", "country": "Mexico"}
  ]
}
```

### Parameterized Test
```typescript
testData.testData.forEach(dataSet => {
  test(`Create supplier - ${dataSet.name}`, async () => {
    await page.fillSupplierName(dataSet.supplierName);
    await page.selectCountry(dataSet.country);  // Different per test
    await page.submit();
  });
});
```

## Summary

✅ **Recorder captures ALL dropdown options** (not just selected one)  
✅ **Generated code accepts ANY option** (data-driven)  
✅ **TypeScript union types** (type-safe)  
✅ **Runtime validation** (optional, catches bad test data)  
✅ **IDE autocomplete** (developer-friendly)  
✅ **Multiple test scenarios** (same code, different data)

**The key insight**: Capturing all options at recording time enables flexible, data-driven tests at generation time!
