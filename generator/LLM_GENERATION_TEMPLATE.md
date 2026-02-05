# Playwright Test Generation Template

When generating test scripts from preview, create 3 files following this exact structure:

## File Naming Convention:
- Test file: `tests/{test-name}.spec.ts` (kebab-case)
- Page file: `pages/{Pagename}page.ts` (PascalCase + lowercase 'page')
- Locator file: `locators/{test-name}.ts` (kebab-case, same as test)

Example: 
- Test: `create-invoice-payables.spec.ts`
- Page: `Createinvoicepayablespage.ts`
- Locator: `create-invoice-payables.ts`

---

## 1. LOCATOR FILE TEMPLATE

**File:** `locators/{test-name}.ts`

```typescript
const locators = {
  elementName1: "xpath=//*[@id=\"...\"]",
  elementName2: "xpath=//*[@id=\"...\"]",
  inputField1: "xpath=//*[@id=\"...\"]",
  buttonName: "xpath=//*[@id=\"...\"]",
};

export default locators;
```

**Rules:**
- Use camelCase for keys
- Always prefix with `xpath=`
- One locator per UI element

---

## 2. PAGE FILE TEMPLATE

**File:** `pages/{Pagename}page.ts`

```typescript
import { Page, Locator } from '@playwright/test';
import HelperClass from "../util/methods.utility.ts";
import locators from "../locators/{test-name}.ts";

class {Pagename}page {
  page: Page;
  helper: HelperClass;
  elementName1: Locator;
  elementName2: Locator;
  inputField1: Locator;
  buttonName: Locator;

  constructor(page: Page) {
    this.page = page;
    this.helper = new HelperClass(page);
    this.elementName1 = page.locator(locators.elementName1);
    this.elementName2 = page.locator(locators.elementName2);
    this.inputField1 = page.locator(locators.inputField1);
    this.buttonName = page.locator(locators.buttonName);
  }

  private coerceValue(value: unknown): string {
    if (value === undefined || value === null) {
      return '';
    }
    if (typeof value === 'number') {
      return `${value}`;
    }
    if (typeof value === 'string') {
      return value;
    }
    return `${value ?? ''}`;
  }

  private normaliseDataKey(value: string): string {
    return (value || '').replace(/[^a-z0-9]+/gi, '').toLowerCase();
  }

  private resolveDataValue(formData: Record<string, any> | null | undefined, key: string, fallback: string = ''): string {
    const target = this.normaliseDataKey(key);
    if (formData) {
      for (const entryKey of Object.keys(formData)) {
        if (this.normaliseDataKey(entryKey) === target) {
          const candidate = this.coerceValue(formData[entryKey]);
          if (candidate.trim() !== '') {
            return candidate;
          }
        }
      }
    }
    return this.coerceValue(fallback);
  }

  async setInputField1(value: unknown): Promise<void> {
    const finalValue = this.coerceValue(value);
    await this.inputField1.fill(finalValue);
  }

  async applyData(formData: Record<string, any> | null | undefined, keys?: string[], index: number = 0): Promise<void> {
    const fallbackValues: Record<string, string> = {
      "InputField1": "",
    };
    const targetKeys = Array.isArray(keys) && keys.length ? keys.map((key) => this.normaliseDataKey(key)) : null;
    const shouldHandle = (key: string) => {
      if (!targetKeys) {
        return true;
      }
      return targetKeys.includes(this.normaliseDataKey(key));
    };
    if (shouldHandle("InputField1")) {
      await this.setInputField1(this.resolveDataValue(formData, "InputField1", fallbackValues["InputField1"] ?? ''));
    }
  }
}

export default {Pagename}page;
```

**Rules:**
- Class name: `{Pagename}page` (PascalCase + lowercase 'page')
- Declare all locators as properties
- Initialize all in constructor
- Include 3 private utility methods: `coerceValue`, `normaliseDataKey`, `resolveDataValue`
- Create `set{FieldName}` methods ONLY for input fields (not buttons/links)
- Include `applyData` method for data-driven testing

**Input Field Detection:**
- Include: text inputs, number inputs, search fields, textareas
- Exclude: buttons, links, icons, actions, validate, close, expand, cells

---

## 3. TEST FILE TEMPLATE

**File:** `tests/{test-name}.spec.ts`

```typescript
import { test } from "./testSetup.ts";
import {Pagename}page from "../pages/{Pagename}page.ts";
import { getTestToRun, shouldRun, readExcelData } from "../util/csvFileManipulation.ts";
import { attachScreenshot, namedStep } from "../util/screenshot.ts";
import * as dotenv from 'dotenv';

const path = require('path');
const fs = require('fs');

dotenv.config();
let executionList: any[];

test.beforeAll(() => {
  executionList = getTestToRun(path.join(__dirname, '../testmanager.xlsx'));
});

test.describe("{Test_name}", () => {
  let {variableName}page: {Pagename}page;

  const run = (name: string, fn: ({ page }, testinfo: any) => Promise<void>) =>
    (shouldRun(name) ? test : test.skip)(name, fn);

  run("{Test_name}", async ({ page }, testinfo) => {
    {variableName}page = new {Pagename}page(page);
    const testCaseId = testinfo.title;
    const testRow: Record<string, any> = executionList?.find((row: any) => row['TestCaseID'] === testCaseId) ?? {};
    const defaultDataStem = (() => {
      const core = testCaseId.replace(/[^a-z0-9]+/gi, ' ').trim();
      if (!core) {
        return 'TestData';
      }
      return core.split(/\s+/).map((part) => part.charAt(0).toUpperCase() + part.slice(1)).join('');
    })();
    const defaultDatasheetName = `${defaultDataStem}Data.xlsx`;
    const defaultIdColumn = `${defaultDataStem}ID`;
    const defaultReferenceId = `${defaultDataStem}001`;
    const dataSheetName = String(testRow?.['DatasheetName'] ?? '').trim() || defaultDatasheetName;
    const envReferenceId = (process.env.REFERENCE_ID || process.env.DATA_REFERENCE_ID || '').trim();
    const excelReferenceId = String(testRow?.['ReferenceID'] ?? '').trim() || defaultReferenceId;
    const dataReferenceId = envReferenceId || excelReferenceId;
    console.log(`[ReferenceID] Using: ${dataReferenceId} (source: ${envReferenceId ? 'env' : 'excel'})`);
    const dataIdColumn = String(testRow?.['IDName'] ?? '').trim() || defaultIdColumn;
    const dataSheetTab = String(testRow?.['SheetName'] ?? testRow?.['Sheet'] ?? '').trim();
    const dataDir = path.join(__dirname, '../data');
    fs.mkdirSync(dataDir, { recursive: true });
    let dataRow: Record<string, any> = {};
    const ensureDataFile = (): string | null => {
      if (!dataSheetName) {
        console.warn(`[DATA] DatasheetName missing for ${testCaseId}; using generated defaults.`);
        return null;
      }
      const expectedPath = path.join(dataDir, dataSheetName);
      if (!fs.existsSync(expectedPath)) {
        const caseInsensitiveMatch = (() => {
          try {
            const entries = fs.readdirSync(dataDir, { withFileTypes: false });
            const target = dataSheetName.toLowerCase();
            const found = entries.find((entry) => entry.toLowerCase() === target);
            return found ? path.join(dataDir, found) : null;
          } catch (err) {
            console.warn(`[DATA] Unable to scan data directory for ${dataSheetName}:`, err);
            return null;
          }
        })();
        if (caseInsensitiveMatch) {
          return caseInsensitiveMatch;
        }
        const message = `Test data file '${dataSheetName}' not found in data/. Upload the file before running '${testCaseId}'.`;
        console.warn(`[DATA] ${message}`);
        throw new Error(message);
      }
      return expectedPath;
    };
    const dataPath = ensureDataFile();
    if (dataPath && dataReferenceId && dataIdColumn) {
      dataRow = readExcelData(dataPath, dataSheetTab || '', dataReferenceId, dataIdColumn) ?? {};
      if (!dataRow || Object.keys(dataRow).length === 0) {
        console.warn(`[DATA] Row not found in ${dataSheetName} for ${dataIdColumn}='${dataReferenceId}'.`);
      }
    } else if (dataSheetName) {
      console.warn(`[DATA] DatasheetName provided but ReferenceID/IDName missing for ${testCaseId}. Generated defaults will be used.`);
    }

    await namedStep("Step 1 - Description", page, testinfo, async () => {
      // Action here
      const screenshot = await page.screenshot();
      attachScreenshot("Step 1 - Description", testinfo, screenshot);
    });

    await namedStep("Step 2 - Enter FieldName", page, testinfo, async () => {
      await {variableName}page.applyData(dataRow, ["FieldName"], 0);
      const screenshot = await page.screenshot();
      attachScreenshot("Step 2 - Enter FieldName", testinfo, screenshot);
    });

    await namedStep("Step 3 - Click ButtonName", page, testinfo, async () => {
      await {variableName}page.buttonName.click();
      const screenshot = await page.screenshot();
      attachScreenshot("Step 3 - Click ButtonName", testinfo, screenshot);
    });

  });
});
```

**Rules:**
- Variable name: lowercase first letter of page name + 'page'
- Include complete Excel data handling block
- Wrap each step in `namedStep`
- Take screenshot after each action
- For input fields: use `applyData(dataRow, ["FieldName"], 0)`
- For clicks: use `{variableName}page.elementName.click()`

---

## COMPLETE EXAMPLE

**Input:** Test for "Create Invoice Payables"

**Output:**

### locators/create-invoice-payables.ts
```typescript
const locators = {
  clickTheElementElement: "xpath=//*[@id=\"pt1:_UISmmLink::icon\"]",
  payables: "xpath=//*[@id=\"pt1:_UISnvr:0:nvgpgl2_groupNode_payables\"]",
  supplier: "xpath=//*[@id=\"_FOpt1:_FOr1:0:_FONSr2:0:MAnt2:1:pm1:r1:0:ap1:r2:0:ic3::content\"]",
  number: "xpath=//*[@id=\"_FOpt1:_FOr1:0:_FONSr2:0:MAnt2:1:pm1:r1:0:ap1:r2:0:i2::content\"]",
  saveAndClose: "xpath=//*[@id=\"_FOpt1:_FOr1:0:_FONSr2:0:MAnt2:1:pm1:r1:0:ap1:cb14\"]",
};

export default locators;
```

### pages/Createinvoicepayablespage.ts
```typescript
import { Page, Locator } from '@playwright/test';
import HelperClass from "../util/methods.utility.ts";
import locators from "../locators/create-invoice-payables.ts";

class Createinvoicepayablespage {
  page: Page;
  helper: HelperClass;
  clickTheElementElement: Locator;
  payables: Locator;
  supplier: Locator;
  number: Locator;
  saveAndClose: Locator;

  constructor(page: Page) {
    this.page = page;
    this.helper = new HelperClass(page);
    this.clickTheElementElement = page.locator(locators.clickTheElementElement);
    this.payables = page.locator(locators.payables);
    this.supplier = page.locator(locators.supplier);
    this.number = page.locator(locators.number);
    this.saveAndClose = page.locator(locators.saveAndClose);
  }

  private coerceValue(value: unknown): string {
    if (value === undefined || value === null) {
      return '';
    }
    if (typeof value === 'number') {
      return `${value}`;
    }
    if (typeof value === 'string') {
      return value;
    }
    return `${value ?? ''}`;
  }

  private normaliseDataKey(value: string): string {
    return (value || '').replace(/[^a-z0-9]+/gi, '').toLowerCase();
  }

  private resolveDataValue(formData: Record<string, any> | null | undefined, key: string, fallback: string = ''): string {
    const target = this.normaliseDataKey(key);
    if (formData) {
      for (const entryKey of Object.keys(formData)) {
        if (this.normaliseDataKey(entryKey) === target) {
          const candidate = this.coerceValue(formData[entryKey]);
          if (candidate.trim() !== '') {
            return candidate;
          }
        }
      }
    }
    return this.coerceValue(fallback);
  }

  async setSupplier(value: unknown): Promise<void> {
    const finalValue = this.coerceValue(value);
    await this.supplier.fill(finalValue);
  }

  async setNumber(value: unknown): Promise<void> {
    const finalValue = this.coerceValue(value);
    await this.number.fill(finalValue);
  }

  async applyData(formData: Record<string, any> | null | undefined, keys?: string[], index: number = 0): Promise<void> {
    const fallbackValues: Record<string, string> = {
      "Supplier": "",
      "Number": "",
    };
    const targetKeys = Array.isArray(keys) && keys.length ? keys.map((key) => this.normaliseDataKey(key)) : null;
    const shouldHandle = (key: string) => {
      if (!targetKeys) {
        return true;
      }
      return targetKeys.includes(this.normaliseDataKey(key));
    };
    if (shouldHandle("Supplier")) {
      await this.setSupplier(this.resolveDataValue(formData, "Supplier", fallbackValues["Supplier"] ?? ''));
    }
    if (shouldHandle("Number")) {
      await this.setNumber(this.resolveDataValue(formData, "Number", fallbackValues["Number"] ?? ''));
    }
  }
}

export default Createinvoicepayablespage;
```

### tests/create-invoice-payables.spec.ts
(Use the test template above with proper variable names)
