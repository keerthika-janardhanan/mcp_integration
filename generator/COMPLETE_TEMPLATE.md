# PLAYWRIGHT CODE GENERATION TEMPLATE

You are generating Playwright test automation code. Follow these templates EXACTLY.

---

## TEMPLATE 1: LOCATOR FILE (locators/{flow-name}.ts)

```typescript
const locators = {
  elementName1: "xpath=//*[@id=\"element-id-1\"]",
  elementName2: "xpath=//*[@id=\"element-id-2\"]",
  elementName3: "xpath=//*[@id=\"element-id-3\"]",
};

export default locators;
```

**Rules for Locators:**
- Use camelCase for property names
- Extract element names from navigation/action text
- Use xpath format: `"xpath=//*[@id=\"...\"]"`
- NO locators for dropdown options (they're selected dynamically)
- Include locators for: buttons, links, input fields, navigation elements

---

## TEMPLATE 2: PAGE FILE (pages/{FlowName}Page.ts)

```typescript
import { Page, Locator } from '@playwright/test';
import HelperClass from "../util/methods.utility.ts";
import locators from "../locators/{flow-name}.ts";

class {FlowName}page {
  page: Page;
  helper: HelperClass;
  // DECLARE ALL LOCATOR PROPERTIES HERE
  elementName1: Locator;
  elementName2: Locator;
  inputField1: Locator;
  inputField2: Locator;

  constructor(page: Page) {
    this.page = page;
    this.helper = new HelperClass(page);
    // INITIALIZE ALL LOCATORS HERE
    this.elementName1 = page.locator(locators.elementName1);
    this.elementName2 = page.locator(locators.elementName2);
    this.inputField1 = page.locator(locators.inputField1);
    this.inputField2 = page.locator(locators.inputField2);
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

  // SETTER METHODS - ONLY FOR INPUT FIELDS (supplier, number, amount, username, password, email, search, text)
  // NO SETTERS FOR: buttons, links, icons, actions, validate, close, expand, cells
  
  async setInputField1(value: unknown): Promise<void> {
    const finalValue = this.coerceValue(value);
    await this.inputField1.fill(finalValue);
  }

  async setInputField2(value: unknown): Promise<void> {
    const finalValue = this.coerceValue(value);
    await this.inputField2.fill(finalValue);
  }

  // applyData method - handles data-driven testing
  async applyData(formData: Record<string, any> | null | undefined, keys?: string[], index: number = 0): Promise<void> {
    const fallbackValues: Record<string, string> = {
      "InputField1": "",
      "InputField2": "",
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
    if (shouldHandle("InputField2")) {
      await this.setInputField2(this.resolveDataValue(formData, "InputField2", fallbackValues["InputField2"] ?? ''));
    }
  }
}

export default {FlowName}page;
```

**Rules for Page Files:**
1. Class name: `{FlowName}page` (e.g., `Createinvoicepayablespage`)
2. MUST include: `helper: HelperClass;` property
3. MUST include: `this.helper = new HelperClass(page);` in constructor
4. Declare ALL locator properties at the top
5. Initialize ALL locators in constructor
6. Include coerceValue, normaliseDataKey, resolveDataValue methods
7. Create setter methods ONLY for input fields (fields where user enters data)
8. Include applyData method for data-driven testing
9. For duplicate field names (e.g., amount appears twice), create amount2, amount3, etc.

---

## TEMPLATE 3: TEST FILE (tests/{flow-name}.spec.ts)

```typescript
import { test } from "./testSetup.ts";
import PageObject from "../pages/{FlowName}Page.ts";
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

test.describe("{Test_Name}", () => {
  let {flowname}page: PageObject;

  const run = (name: string, fn: ({ page }, testinfo: any) => Promise<void>) =>
    (shouldRun(name) ? test : test.skip)(name, fn);

  run("{Test_Name}", async ({ page }, testinfo) => {
    {flowname}page = new PageObject(page);
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
    const normaliseKey = (value: string) => value.replace(/[^a-z0-9]/gi, '').toLowerCase();
    const findMatchingDataKey = (sourceKey: string) => {
      if (!sourceKey || !dataRow) {
        return undefined;
      }
      const normalisedSource = normaliseKey(sourceKey);
      return Object.keys(dataRow || {}).find((candidate) => normaliseKey(String(candidate)) === normalisedSource);
    };
    const getDataValue = (sourceKey: string, fallback: string) => {
      if (!sourceKey) {
        return fallback;
      }
      const directKey = findMatchingDataKey(sourceKey) || findMatchingDataKey(sourceKey.replace(/([A-Z])/g, '_$1'));
      if (directKey) {
        const candidate = dataRow?.[directKey];
        if (candidate !== undefined && candidate !== null && `${candidate}`.trim() !== '') {
          return `${candidate}`;
        }
      }
      return fallback;
    };
    const dataSheetPath = path.join(__dirname, '../testdata', dataSheetName);
    let dataRow: Record<string, any> = {};

    if (fs.existsSync(dataSheetPath)) {
      dataRow = readExcelData(dataSheetPath, dataSheetTab || '', dataReferenceId, dataIdColumn) || {};
    } else {
      const altPath = path.join(__dirname, '../data', dataSheetName);
      if (fs.existsSync(altPath)) {
        dataRow = readExcelData(altPath, dataSheetTab || '', dataReferenceId, dataIdColumn) || {};
      }
    }

    // TEST STEPS
    await namedStep("Step 1 - Click element", page, testinfo, async () => {
      // Click element
      await {flowname}page.elementName.click();
      // Expected: Element responds as expected.
      const screenshot = await page.screenshot();
      attachScreenshot("Step 1 - Click element", testinfo, screenshot);
    });

    await namedStep("Step 2 - Enter data", page, testinfo, async () => {
      // Enter data
      await {flowname}page.applyData(dataRow, ["FieldName"], 0);
      // Expected: Field captures the entered data.
      const screenshot = await page.screenshot();
      attachScreenshot("Step 2 - Enter data", testinfo, screenshot);
    });

  });
});
```

**Rules for Test Files:**
1. MUST include complete Excel data handling block (lines 23-110)
2. Step 0 is ALWAYS login step
3. Each action wrapped in `namedStep`
4. Screenshot after EVERY step
5. For input fields: `await pagename.applyData(dataRow, ["FieldName"], index);`
6. For clicks: `await pagename.elementName.click();`
7. For duplicate fields (e.g., Amount appears twice):
   - First occurrence: `await pagename.applyData(dataRow, ["Amount"], 0);`
   - Second occurrence: `await pagename.applyData(dataRow, ["Amount"], 1);`

---

## GENERATION INSTRUCTIONS

When generating code:

1. **Analyze the recorded steps** to identify:
   - Input fields (supplier, number, amount, username, password, email, search)
   - Click actions (buttons, links, navigation)
   - Data fields that need Excel mapping

2. **Generate locators file**:
   - Extract element names from step navigation/action text
   - Use camelCase naming
   - Use xpath format

3. **Generate page file**:
   - Class name: `{FlowName}page` (lowercase 'page')
   - Include HelperClass import and property
   - Declare ALL locator properties
   - Initialize ALL locators in constructor
   - Create setter methods ONLY for input fields
   - Include applyData method with proper field mapping

4. **Generate test file**:
   - Include complete Excel data block
   - Step 0 = Login
   - Wrap each action in namedStep
   - Use applyData for input fields
   - Use .click() for buttons/links
   - Handle duplicate fields with index parameter

5. **Return JSON format**:
```json
{
  "locators/{flow-name}.ts": "...",
  "pages/{FlowName}Page.ts": "...",
  "tests/{flow-name}.spec.ts": "..."
}
```

Generate complete, working code. NO placeholders. NO TODOs. NO empty methods.
