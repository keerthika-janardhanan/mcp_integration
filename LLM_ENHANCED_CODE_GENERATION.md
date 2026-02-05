# LLM-Enhanced Code Generation System

## Overview

The enhanced code generation system uses LLM (Copilot) to analyze framework repositories and generate intelligent, production-ready Playwright test automation code that:

1. **Detects and reuses existing framework components** (login pages, base pages, utilities)
2. **Follows established coding standards** from the framework
3. **Handles dynamic elements intelligently** (tables, dropdowns, loading indicators)
4. **Adds appropriate wait conditions** based on flow understanding
5. **Creates flexible selectors** for data-driven testing

## Architecture

### Components

1. **FrameworkTemplate** (Static Templates)
   - Provides baseline template structure
   - Used as fallback when LLM is unavailable
   - Located in `templates/` directory

2. **LLMEnhancedGenerator** (Intelligent Generation)
   - Analyzes framework repository for reusable code
   - Generates context-aware code using LLM
   - Handles dynamic elements and wait conditions
   - Located in `app/generators/framework_templates.py`

### Workflow

```
1. User records flow → Recorder captures steps with metadata
                           ↓
2. Finalize recording → Auto-ingest processes and stores in vector DB
                           ↓
3. Generate script → AgenticScriptAgent triggered
                           ↓
4. Framework Analysis → LLM scans framework repo for reusable components
                           ↓
5. Enhanced Generation → LLM generates code using:
                         - Reusable components (LoginPage, BasePage)
                         - Coding standards from framework
                         - Smart wait conditions
                         - Flexible table/dropdown selectors
                           ↓
6. Output → 4 files: locators, pages, tests, test_data
```

## Framework Analysis

### What LLM Analyzes

When analyzing a framework repository, the LLM looks for:

1. **Reusable Components**
   - Login/Authentication pages (`login*.ts`, `auth*.ts`)
   - Home/Dashboard pages (`home*.ts`, `dashboard*.ts`)
   - Base classes (`base*.ts`, `base-page*.ts`)
   - Common page objects

2. **Utility Functions**
   - Wait helpers (`wait*.ts`, `*-helpers.ts`)
   - Excel/file handling utilities
   - Custom matchers and assertions
   - Data generation utilities

3. **Coding Standards**
   - Naming conventions (PascalCase, camelCase, snake_case)
   - Import patterns
   - Page Object Model structure
   - Error handling patterns

4. **Dynamic Element Patterns**
   - Table row selection strategies
   - Dropdown/select handling
   - Loading indicator patterns
   - Dynamic content waiting

### Example Analysis Output

```json
{
  "reusable_components": [
    {
      "name": "LoginPage",
      "import": "../pages/login.page",
      "methods": ["login", "logout", "isLoggedIn"],
      "description": "Handles user authentication with SSO support"
    },
    {
      "name": "BasePage",
      "import": "../pages/base.page",
      "methods": ["navigate", "waitForReady", "handleErrors"],
      "description": "Base class for all page objects with common utilities"
    }
  ],
  "coding_standards": [
    {
      "pattern": "Page Object Model",
      "description": "All pages extend BasePage class"
    },
    {
      "pattern": "Locator Separation",
      "description": "Locators defined in separate .locators.ts files"
    }
  ],
  "utilities": [
    {
      "name": "waitForTableLoad",
      "import": "../utils/wait.helpers",
      "description": "Waits for dynamic table to finish loading"
    },
    {
      "name": "selectTableRowByName",
      "import": "../utils/table.helpers",
      "description": "Selects table row by name, not index"
    }
  ],
  "dynamic_patterns": [
    {
      "pattern": "table-row-by-name",
      "code": "page.locator('table tr').filter({ hasText: rowName })"
    },
    {
      "pattern": "wait-for-loading",
      "code": "await page.locator('.loading').waitFor({ state: 'hidden' })"
    }
  ]
}
```

## Dynamic Element Handling

### Table Selection Strategies

**Problem**: During recording, user might click the first row or a specific row by name. Test script needs flexible selection.

**Solution**: LLM generates flexible locators:

```typescript
// Generated Locator
tableRowByText(text: string): Locator {
  return this.page.getByRole('row').filter({ hasText: text });
}

tableRowByIndex(index: number): Locator {
  return this.page.locator(`table tbody tr:nth-child(${index})`);
}

// Generated Page Method
async selectTableRowByText(rowText: string): Promise<void> {
  const row = this.locators.tableRowByText(rowText);
  await row.waitFor({ state: 'visible' });
  await row.click();
  await this.waitForDynamicContent();
}
```

**Usage in Test**:
```typescript
// Data-driven selection
await page.selectTableRowByText(testData.supplierName); // Not hardcoded index!
```

### Dropdown Handling

**Generated Code**:
```typescript
// Use semantic locators with label-based selection
async selectCountry(country: string): Promise<void> {
  const dropdown = this.locators.countryDropdown;
  await dropdown.waitFor({ state: 'visible' });
  await dropdown.selectOption({ label: country }); // By label, not value
}
```

### Loading Indicators

**Generated Wait Logic**:
```typescript
async waitForDynamicContent(): Promise<void> {
  // Wait for common loading indicators
  const loadingSelectors = ['.loading', '.spinner', '[data-loading="true"]'];
  for (const selector of loadingSelectors) {
    const loading = this.page.locator(selector);
    if (await loading.isVisible().catch(() => false)) {
      await loading.waitFor({ state: 'hidden', timeout: 10000 });
    }
  }
  await this.page.waitForLoadState('networkidle');
}
```

## Coding Standards Enforcement

### Locator Priority

1. **Playwright Semantic** (First Priority)
   - `getByRole('button', { name: 'Submit' })`
   - `getByLabel('Email Address')`
   - `getByText('Create Supplier')`
   - `getByPlaceholder('Enter name')`

2. **CSS Selectors** (Second Priority)
   - `.submit-button`
   - `#email-input`
   - `[data-testid="supplier-form"]`

3. **XPath** (Last Resort)
   - Only when semantic locators not possible

### Naming Conventions

- **Classes**: PascalCase (`CreateSupplierPage`, `LoginPage`)
- **Methods**: camelCase (`selectTableRow`, `fillSupplierName`)
- **Files**: snake_case (`create_supplier.page.ts`, `login.spec.ts`)
- **Locators**: descriptive (`submitButton`, `supplierNameInput`)

### Base Class Extension

**Generated Code Automatically Extends Base**:
```typescript
import { BasePage } from './base.page';

export class CreateSupplierPage extends BasePage {
  constructor(page: Page) {
    super(page); // Inherits common utilities
  }
  
  // Framework-specific methods available through BasePage
}
```

## Reusable Component Integration

### Login Page Reuse

**LLM detects existing LoginPage and generates**:

```typescript
// In test file
import { LoginPage } from '../pages/login.page';

test.beforeEach(async ({ page }) => {
  // Reuse existing login functionality
  const loginPage = new LoginPage(page);
  await loginPage.navigate(process.env.BASE_URL);
  await loginPage.login(
    process.env.USERNAME || 'testuser',
    process.env.PASSWORD || 'password'
  );
  await page.waitForURL('**/home');
  
  // Now proceed with test-specific actions
  const supplierPage = new CreateSupplierPage(page);
  // ...
});
```

### Utility Function Reuse

**LLM detects wait helpers and uses them**:

```typescript
import { waitForTableLoad } from '../utils/wait.helpers';

async fillSupplierForm(data: SupplierData): Promise<void> {
  // Use framework utilities
  await waitForTableLoad(this.page, 'suppliers-table');
  
  // Fill form fields
  // ...
}
```

## Test Data Mapping

### Enhanced Test Data Structure

```json
{
  "flowName": "Create Supplier",
  "testData": [
    {
      "name": "happy_path",
      "description": "Standard supplier creation",
      "fields": [
        {
          "fieldName": "supplierName",
          "step": 1,
          "action": "fill",
          "sampleValue": "ACME Corporation",
          "required": true,
          "dataType": "string",
          "validationRules": {
            "minLength": 3,
            "maxLength": 100,
            "pattern": "^[A-Za-z0-9 ]+$"
          }
        },
        {
          "fieldName": "countrySelection",
          "step": 3,
          "action": "select",
          "sampleValue": "United States",
          "required": true,
          "dataType": "dropdown",
          "selectionMethod": "by-label"
        },
        {
          "fieldName": "supplierTableRow",
          "step": 5,
          "action": "click",
          "sampleValue": "ACME Corporation",
          "required": true,
          "dataType": "table-selection",
          "selectionCriteria": "by-name"
        }
      ]
    }
  ],
  "dynamicElements": {
    "tables": {
      "selectionStrategy": "by-text-content",
      "note": "Use row name for flexible selection"
    },
    "loadingIndicators": [".loading", ".spinner"]
  }
}
```

## Usage

### Enable LLM Enhancement

**In agentic_script_agent.py**:

```python
# Method signature includes use_llm_enhancement flag
payload = self._generate_payload_with_templates(
    scenario=scenario,
    framework=framework,
    accepted_preview=preview,
    vector_steps=steps,
    use_llm_enhancement=True  # Enable LLM enhancement
)
```

### API Endpoint

**Frontend calls**:
```javascript
const response = await axios.post('/api/script/generate', {
  scenario: "Create Supplier automation script",
  framework_path: "/path/to/framework",
  recording_session: "session_123",
  use_llm_enhancement: true
});
```

### Fallback Behavior

If LLM fails or is unavailable:
1. System logs warning
2. Falls back to static templates
3. Generates basic code without framework analysis
4. Still produces functional code, just without reusability enhancements

## Benefits

### 1. Code Reusability
- Automatically imports and uses existing LoginPage
- Extends BasePage for common utilities
- Uses framework-specific helpers

### 2. Maintainability
- Follows established patterns
- Consistent naming conventions
- Centralized test data management

### 3. Flexibility
- Table rows selected by name, not index
- Dropdowns selected by label, not value
- Works across different data sets

### 4. Reliability
- Appropriate wait conditions added automatically
- Handles dynamic content loading
- Error scenarios included

### 5. Smart Adaptation
- Learns from existing framework code
- Adapts to project-specific patterns
- Generates context-aware code

## Configuration

### Environment Variables

```bash
# LLM Configuration (for Copilot API)
AZURE_OPENAI_KEY=your-key
AZURE_OPENAI_ENDPOINT=https://your-endpoint
OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_DEPLOYMENT=your-deployment

# Framework Settings
FRAMEWORK_ANALYSIS_ENABLED=true
FRAMEWORK_ROOT=/path/to/framework

# Code Generation
USE_LLM_ENHANCEMENT=true
FALLBACK_TO_TEMPLATES=true
```

### Customization

**Add custom patterns to analysis**:

Edit `framework_templates.py`:
```python
# Extend _classify_file_type for custom patterns
def _classify_file_type(self, path: str) -> str:
    path_lower = path.lower()
    if 'excel' in path_lower or 'xlsx' in path_lower:
        return 'excel_utility'
    # Add more custom classifications
```

## Examples

### Before (Static Template)

```typescript
// Basic, no reusability
async step3_select(option: string) {
  await this.locators.step3Element.selectOption(option);
}
```

### After (LLM Enhanced)

```typescript
// Extends BasePage, uses utilities, smart waits
import { BasePage } from './base.page';
import { waitForDropdownLoad } from '../utils/wait.helpers';

export class CreateSupplierPage extends BasePage {
  async selectCountry(country: string): Promise<void> {
    await waitForDropdownLoad(this.page, 'country-dropdown');
    const dropdown = this.locators.countryDropdown;
    await dropdown.selectOption({ label: country });
    await this.waitForDynamicContent();
  }
}
```

## Troubleshooting

### Issue: LLM not detecting reusable components

**Solution**: Ensure framework has standard naming:
- Login pages: `login.page.ts`, `auth.page.ts`
- Base classes: `base.page.ts`, `base-page.ts`
- Utilities: `*-helpers.ts`, `*-utils.ts`

### Issue: Generated code doesn't extend BasePage

**Solution**: Check framework analysis output in logs:
```bash
[LLM Analysis] Found 0 reusable components
```
Verify base page exists and is readable.

### Issue: Table selectors still using index

**Solution**: Ensure step has `visibleText` field from recorder:
```json
{
  "step": 5,
  "action": "click",
  "visibleText": "ACME Corporation"
}
```

## Future Enhancements

1. **Framework Pattern Learning**
   - Learn from existing test patterns
   - Suggest improvements to framework structure

2. **Custom Wait Strategies**
   - Detect custom wait functions in framework
   - Apply them automatically

3. **Excel Integration Detection**
   - Detect Excel utilities in framework
   - Generate Excel-driven test data loading

4. **Multi-Framework Support**
   - Detect framework type (Playwright, Selenium, Cypress)
   - Generate appropriate code for each

5. **Self-Healing Locators**
   - Store alternative locators in test data
   - Auto-retry with alternatives on failure

---

**Last Updated**: 2026-01-28
**Version**: 2.0 (LLM Enhanced)
