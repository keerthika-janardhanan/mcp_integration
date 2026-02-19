# PLAYWRIGHT TEST SCRIPT GENERATOR

Generate Playwright TypeScript test files. Output ONLY valid JSON.

## OUTPUT FORMAT

```json
{
  "locators/PageName.ts": "export default { field: 'selector' }",
  "pages/PageName.pages.ts": "class PageNamePage { ... } export default PageNamePage;",
  "tests/flow-name.spec.ts": "test.describe(...)"
}
```

## CRITICAL RULES

### 1. LOCATOR PRIORITY (use first available from recorder metadata)

**a) Playwright properties - CONVERT to CSS equivalents for page.locator():**
- `getByTestId('id')` → `[data-testid='id']`
- `getByRole('button', { name: 'Text' })` → `button[aria-label='Text']`
- `getByLabel('Label')` → `[aria-label='Label']`
- `getByPlaceholder('Text')` → `[placeholder='Text']`
- `getByText('Text')` → `text='Text'`

**b) CSS selector:** `input[name='user']`, `button[type='submit']`

**c) XPath (LAST RESORT):** `xpath=//*[@id='username']`

**d) Combine attributes if needed:** `input[name='user'][type='text']`

**NEVER guess locators - use ONLY recorder metadata**

### 2. PAGE SEPARATION

Create separate locator/page files per [Page Title]

Example: `[Login Page]` → `locators/LoginPage.ts` + `pages/LoginPage.pages.ts`

If multiple pages detected, create one file per page.

### 3. PAGE CLASS STRUCTURE

```typescript
import { Page, Locator } from '@playwright/test';
import HelperClass from "../util/methods.utility.ts";
import locators from "../locators/PageName.ts";

class PageNamePage {
  page: Page;
  helper: HelperClass;
  elementName: Locator;

  constructor(page: Page) {
    this.page = page;
    this.helper = new HelperClass(page);
    this.elementName = page.locator(locators.elementName);
  }

  private coerceValue(value: unknown): string {
    if (value === undefined || value === null) return '';
    if (typeof value === 'number') return `${value}`;
    if (typeof value === 'string') return value;
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
          if (candidate.trim() !== '') return candidate;
        }
      }
    }
    return this.coerceValue(fallback);
  }

  async setFieldName(value: unknown): Promise<void> {
    const finalValue = this.coerceValue(value);
    await this.elementName.fill(finalValue);
  }

  async applyData(formData: Record<string, any> | null | undefined, keys?: string[], index: number = 0): Promise<void> {
    const fallbackValues: Record<string, string> = { "FieldName": "" };
    const targetKeys = Array.isArray(keys) && keys.length ? keys.map((key) => this.normaliseDataKey(key)) : null;
    const shouldHandle = (key: string) => !targetKeys || targetKeys.includes(this.normaliseDataKey(key));
    if (shouldHandle("FieldName")) {
      await this.setFieldName(this.resolveDataValue(formData, "FieldName", fallbackValues["FieldName"] ?? ''));
    }
  }
}

export default PageNamePage;
```

**Requirements:**
- Import: Page, Locator, HelperClass, locators
- Properties: page, helper, locators as Locator
- Constructor: initialize helper and locators
- Methods: coerceValue, normaliseDataKey, resolveDataValue, applyData
- applyData reads from formData (Excel data from ../data/)
- NEVER use process.env - ALL data from Excel
- Export: export default PageClass;

### 4. TEST FILE

```typescript
import { test } from './testSetup';
import PageNamePage from '../pages/PageNamePage.pages';
import { getTestToRun, shouldRun, readExcelData } from '../util/csvFileManipulation';
import { attachScreenshot, namedStep } from '../util/screenshot';

const path = require('path');
const fs = require('fs');

let executionList: any[];

test.beforeAll(() => {
  executionList = getTestToRun(path.join(__dirname, '../testmanager.xlsx'));
});

test.describe('test-name', () => {
  let pageNamePage: PageNamePage;

  const run = (name: string, fn: ({ page }, testinfo: any) => Promise<void>) =>
    (shouldRun(name) ? test : test.skip)(name, fn);

  run('test-name', async ({ page }, testinfo) => {
    pageNamePage = new PageNamePage(page);
    
    const testCaseId = testinfo.title;
    const testRow: Record<string, any> = executionList?.find((row: any) => row['TestCaseID'] === testCaseId) ?? {};
    
    const defaultDataStem = (() => {
      const core = testCaseId.replace(/[^a-z0-9]+/gi, ' ').trim();
      if (!core) return 'TestData';
      return core.split(/\s+/).map((part) => part.charAt(0).toUpperCase() + part.slice(1)).join('');
    })();
    
    const defaultDatasheetName = `${defaultDataStem}Data.xlsx`;
    const defaultIdColumn = `${defaultDataStem}ID`;
    const defaultReferenceId = `${defaultDataStem}001`;
    
    const dataSheetName = String(testRow?.['DatasheetName'] ?? '').trim() || defaultDatasheetName;
    const idColumn = String(testRow?.['IDName'] ?? '').trim() || defaultIdColumn;
    const excelReferenceId = String(testRow?.['ReferenceID'] ?? '').trim() || defaultReferenceId;
    const sheetTab = String(testRow?.['SheetTab'] ?? '').trim() || 'Sheet1';
    
    const dataPath = path.join(__dirname, '../data', dataSheetName);
    
    if (!fs.existsSync(dataPath)) {
      throw new Error(`Data file not found: ${dataPath}`);
    }
    
    const dataRow = readExcelData(dataPath, sheetTab, excelReferenceId, idColumn);
    
    if (!dataRow || Object.keys(dataRow).length === 0) {
      throw new Error(`No data found for ReferenceID: ${excelReferenceId} in ${dataSheetName}`);
    }

    await namedStep('Step 1 - Action description', page, testinfo, async () => {
      // Comment describing the action
      await pageNamePage.elementName.click();
      const screenshot = await page.screenshot();
      attachScreenshot('Step 1 - Action description', testinfo, screenshot);
    });

    await namedStep('Step 2 - Enter data', page, testinfo, async () => {
      // Fill input field with Excel data
      await pageNamePage.applyData(dataRow, ['FieldName'], 0);
      const screenshot = await page.screenshot();
      attachScreenshot('Step 2 - Enter data', testinfo, screenshot);
    });
  });
});
```

**Requirements:**
- Import: test, page classes, getTestToRun, readExcelData, namedStep, attachScreenshot
- beforeAll: load testmanager.xlsx
- Initialize page objects
- Step format: `await namedStep('Step N - Action description', page, testInfo, async () => { ... });`
- Inside step: comment, action, screenshot capture, attachScreenshot call
- Load Excel data: `readExcelData(path, sheetName, referenceId, columnName)`
- Use IDName from testmanager (NOT IDColumn): `const idColumn = String(testRow?.['IDName'] ?? '').trim() || defaultIdColumn;`
- Call applyData with dataRow and column names

### 5. DATA HANDLING

- Path: `path.join(__dirname, '../data', dataSheetName)`
- Read: `readExcelData(path, sheetTab, referenceId, idColumn)`
- Apply: `await page.applyData(dataRow, ['Column1', 'Column2'], index)`
- Validate: throw if dataRow empty

## IMPORTANT NOTES

- Generate complete JSON. No markdown fences. No placeholders.
- Use ONLY locators from recorder metadata
- Create separate files per page when multiple pages detected
- Always include all 3 utility methods in page classes
- Always wrap steps in namedStep with screenshots
- Use IDName (not IDColumn) from testmanager.xlsx
