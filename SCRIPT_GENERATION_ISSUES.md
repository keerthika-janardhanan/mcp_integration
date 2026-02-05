# Script Generation Issues & Fixes Required

## Issues Identified

### 1. **Invalid Class Names** (Critical)
**Problem**: When scenario name starts with numbers (e.g., "123test"), generated code creates invalid TypeScript identifiers:
```typescript
import { 123testPage } from '../pages/123test.page';  // ❌ Invalid!
let page: 123testPage;  // ❌ Invalid!
```

**Root Cause**: `_to_camel_case()` in [agentic_script_agent.py](app/agentic_script_agent.py#L63-L70) doesn't handle leading numbers.

**Fix Required**:
```python
def _to_camel_case(value: str) -> str:
    if not value:
        return ""
    cleaned = re.sub(r"['\"_]+", " ", str(value))
    cleaned = re.sub(r"\s+", " ", cleaned).strip().lower()
    if not cleaned:
        return ""
    # Remove leading numbers
    cleaned = re.sub(r"^[0-9]+", "", cleaned)
    if not cleaned:
        return "Generated"
    # Ensure first char is letter
    result = re.sub(r"[^a-z0-9]+(.)?", lambda m: m.group(1).upper() if m.group(1) else "", cleaned)
    if result and result[0].isdigit():
        result = "Test" + result
    return result or "Generated"
```

---

### 2. **Wrong Template Used** (Critical)
**Problem**: Generated code uses generic Playwright template instead of framework-specific patterns.

**Expected Pattern** (from actual framework):
```typescript
import { test } from "./testSetup.ts";
import PageObject from "../pages/CreateinvoicepayablesPage.ts";
import LoginPage from "../pages/login.page.ts";
import { getTestToRun, shouldRun, readExcelData } from "../util/csvFileManipulation.ts";
import { attachScreenshot, namedStep } from "../util/screenshot.ts";

test.describe("Create_invoice_payables", () => {
  let createinvoicepayablespage: PageObject;
  let loginPage: LoginPage;
  
  const run = (name: string, fn: ({ page }, testinfo: any) => Promise<void>) =>
    (shouldRun(name) ? test : test.skip)(name, fn);

  run("Create_invoice_payables", async ({ page }, testinfo) => {
    // Excel-based test data loading
    const testRow = executionList?.find((row) => row['TestCaseID'] === testCaseId) ?? {};
    const dataRow = readExcelData(dataPath, dataSheetTab, dataReferenceId, dataIdColumn);
    
    // Named steps with screenshots
    await namedStep("Step 14 - Enter Supplier", page, testinfo, async () => {
      await createinvoicepayablespage.applyData(dataRow, ["Supplier"], 0);
      const screenshot = await page.screenshot();
      attachScreenshot("Step 14 - Enter Supplier", testinfo, screenshot);
    });
  });
});
```

**Generated Pattern** (Wrong):
```typescript
import { test, expect } from '@playwright/test';
import { 123testPage } from '../pages/123test.page';
import testData from '../data/123test_data.json';

test.describe('123test', () => {
  test('123test - Happy Path', async () => {
    await page.step2_click();
    await page.step4_click();
  });
});
```

**Root Cause**: The deterministic payload generation in `_build_deterministic_payload()` at [agentic_script_agent.py](app/agentic_script_agent.py#L1399-L2043) is being used, which generates the correct structure internally, but something is using the wrong template.

---

### 3. **Missing Framework Features** (Critical)

The generated code is missing essential framework patterns:

#### A) **Test Manager Integration**
```typescript
// ❌ Missing:
import { getTestToRun, shouldRun, readExcelData } from "../util/csvFileManipulation.ts";
const executionList = getTestToRun(path.join(__dirname, '../testmanager.xlsx'));
const run = (name: string, fn) => (shouldRun(name) ? test : test.skip)(name, fn);
```

#### B) **Excel-based Test Data**
```typescript
// ❌ Missing:
const dataRow = readExcelData(dataPath, dataSheetTab, dataReferenceId, dataIdColumn);
await createinvoicepayablespage.applyData(dataRow, ["Supplier"], 0);
```

#### C) **Named Steps with Screenshots**
```typescript
// ❌ Missing:
await namedStep("Step 14 - Enter Supplier", page, testinfo, async () => {
  await createinvoicepayablespage.applyData(dataRow, ["Supplier"], 0);
  const screenshot = await page.screenshot();
  attachScreenshot("Step 14 - Enter Supplier", testinfo, screenshot);
});
```

#### D) **Login Page Integration**
```typescript
// ❌ Missing:
await namedStep("Step 0 - Login", page, testinfo, async () => {
  await loginPage.goto();
  await loginPage.login(process.env.USERID ?? '', process.env.PASSWORD ?? '');
});
```

---

### 4. **Page Object Issues**

**Generated** (simplified, wrong):
```typescript
class 123testPage {
  constructor(page: Page) {
    this.page = page;
  }
  
  async step2_click() {
    // Just click, no data handling
  }
}
```

**Expected** (from framework):
```typescript
class Createinvoicepayablespage {
  page: Page;
  helper: HelperClass;
  supplier: Locator;
  number: Locator;
  amount: Locator;
  amount2: Locator;

  constructor(page: Page) {
    this.page = page;
    this.helper = new HelperClass(page);
    this.supplier = page.locator(locators.supplier);
    this.number = page.locator(locators.number);
    this.amount = page.locator(locators.amount);
    this.amount2 = page.locator(locators.amount2);
  }

  async setSupplier(value: unknown): Promise<void> {
    await this.supplier.fill(this.coerceValue(value));
  }

  async applyData(formData: Record<string, any>, keys?: string[], index: number = 0): Promise<void> {
    if (shouldHandle("Supplier")) {
      await this.setSupplier(this.resolveDataValue(formData, "Supplier", ""));
    }
    if (shouldHandle("Amount")) {
      const value = this.resolveDataValue(formData, "Amount", "");
      if (index === 0) await this.setAmount(value);
      else if (index === 1) await this.setAmount2(value);
    }
  }
}
```

---

### 5. **Locators File Issues**

**Generated** (empty or minimal):
```typescript
export class 123testLocators {
  // Mostly empty
}
```

**Expected**:
```typescript
const locators = {
  supplier: "xpath=//*[@id=\"...\"]",
  number: "xpath=//*[@id=\"...\"]",
  amount: "xpath=//*[@id=\"...\"]",
  amount2: "xpath=//*[@id=\"...\"]",
};

export default locators;
```

---

## Where the Issue Occurs

The problem is likely in **how the generated files are displayed/used**, not in the generation itself. Looking at the deterministic payload generation at line 1399-2043, it DOES generate:
- ✅ Proper imports with `testSetup.ts`
- ✅ Excel integration with `getTestToRun`, `readExcelData`
- ✅ Named steps with `namedStep()`
- ✅ Screenshot attachments
- ✅ Login page handling
- ✅ `applyData()` with multi-occurrence support

**BUT** - The user is seeing the wrong template output. This suggests:

1. **Frontend is using the wrong template** - Check [frontend/src/components](frontend/src/components) for how it displays generated code
2. **Template files are being used instead of deterministic generation** - The templates in [templates/](templates/) are generic Playwright patterns, not framework-specific
3. **LLM payload generation is enabled** - When `USE_LLM_PAYLOAD=true`, it bypasses deterministic generation

---

## Required Fixes

### Fix 1: Update `_to_camel_case()` in agentic_script_agent.py
Location: [agentic_script_agent.py](app/agentic_script_agent.py#L63-L70)

```python
def _to_camel_case(value: str) -> str:
    if not value:
        return ""
    cleaned = re.sub(r"['\"_]+", " ", str(value))
    cleaned = re.sub(r"\s+", " ", cleaned).strip().lower()
    if not cleaned:
        return ""
    # Remove leading numbers
    cleaned = re.sub(r"^[0-9]+", "", cleaned).strip()
    if not cleaned:
        return "Generated"
    # Convert to camelCase
    result = re.sub(r"[^a-z0-9]+(.)?", lambda m: m.group(1).upper() if m.group(1) else "", cleaned)
    # Ensure doesn't start with number
    if result and result[0].isdigit():
        result = "Test" + result
    return result or "Generated"
```

### Fix 2: Ensure Deterministic Generation is Used
Location: [agentic_script_agent.py](app/agentic_script_agent.py#L1287-L1296)

Check that `USE_LLM_PAYLOAD` environment variable is NOT set or is `false`:
```python
# Around line 1293
use_llm_payload = str(os.getenv("USE_LLM_PAYLOAD", "")).strip().lower() in {"1", "true", "yes", "on"}
```

**Recommendation**: Default should be deterministic generation, as it matches the framework patterns.

### Fix 3: Update Templates (If Used)
If templates are being used instead of deterministic generation, update:
- [templates/playwright_test.spec.ts.template](templates/playwright_test.spec.ts.template)
- [templates/playwright_page.ts.template](templates/playwright_page.ts.template)
- [templates/playwright_locator.ts.template](templates/playwright_locator.ts.template)

Replace generic Playwright patterns with framework-specific patterns from the actual repo.

### Fix 4: Frontend Display
Check where the frontend renders generated code. It should:
1. Show all 3 files (locators, pages, tests)
2. Make them editable
3. Include test data mapping UI
4. Pull from deterministic generation output, not templates

Likely locations:
- `frontend/src/components/ScriptGenerator.tsx` (or similar)
- API endpoint that returns generated files
- Check [app/api/routers/](app/api/routers/) for script generation endpoints

---

## Testing the Fix

After applying fixes, test with scenario "123test":

**Expected Output**:

**File: locators/test123.ts**
```typescript
const locators = {
  step2: "xpath=...",
  step4: "xpath=...",
  // ... other selectors
};

export default locators;
```

**File: pages/Test123Page.ts** (note: capitalized, no leading number)
```typescript
import { Page, Locator } from '@playwright/test';
import HelperClass from "../util/methods.utility.ts";
import locators from "../locators/test123.ts";

class Test123page {
  page: Page;
  helper: HelperClass;
  step2: Locator;
  step4: Locator;
  
  constructor(page: Page) {
    this.page = page;
    this.helper = new HelperClass(page);
    this.step2 = page.locator(locators.step2);
    this.step4 = page.locator(locators.step4);
  }
  
  async applyData(formData, keys?, index = 0) {
    // Framework-specific data binding logic
  }
}

export default Test123page;
```

**File: tests/test123.spec.ts**
```typescript
import { test } from "./testSetup.ts";
import PageObject from "../pages/Test123Page.ts";
import LoginPage from "../pages/login.page.ts";
import { getTestToRun, shouldRun, readExcelData } from "../util/csvFileManipulation.ts";
import { attachScreenshot, namedStep } from "../util/screenshot.ts";

test.describe("Test123", () => {
  let test123page: PageObject;
  let loginPage: LoginPage;
  
  const run = (name: string, fn) => (shouldRun(name) ? test : test.skip)(name, fn);
  
  run("Test123", async ({ page }, testinfo) => {
    test123page = new PageObject(page);
    loginPage = new LoginPage(page);
    
    // Excel-based test data loading
    const dataRow = readExcelData(...);
    
    await namedStep("Step 2 - ...", page, testinfo, async () => {
      await test123page.step2.click();
      const screenshot = await page.screenshot();
      attachScreenshot("Step 2 - ...", testinfo, screenshot);
    });
  });
});
```

---

## UI/Frontend Issues

Based on your description, the UI should have:
1. **Test data mapping section** - with editable fields
2. **3 code panels** - showing locators, pages, tests
3. **Edit capability** - for all generated code
4. **Proper formatting** - matching framework conventions

Check these frontend files:
- `frontend/src/components/` - React components for code display
- `frontend/src/pages/` - Page-level components
- API endpoints in `app/api/routers/` - ensure they return proper deterministic payload

The frontend likely needs to:
1. Call the correct API endpoint that uses deterministic generation
2. Display all 3 files from the payload: `payload.locators[0]`, `payload.pages[0]`, `payload.tests[0]`
3. Provide editors (like Monaco Editor or CodeMirror) for each file
4. Include test data mapping UI separate from code display
