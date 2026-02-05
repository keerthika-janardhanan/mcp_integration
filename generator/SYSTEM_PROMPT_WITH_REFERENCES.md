# PLAYWRIGHT TEST GENERATOR - FINAL SYSTEM PROMPT

Generate 3 files using these EXACT reference templates. Copy the structure precisely.

---

## REFERENCE PAGE FILE (COPY THIS STRUCTURE)

```typescript
import { Page, Locator } from '@playwright/test';
import HelperClass from "../util/methods.utility.ts";
import locators from "../locators/create-invoice-payables.ts";

class Createinvoicepayablespage {
  page: Page;
  helper: HelperClass;
  clickTheElementElement: Locator;
  payables: Locator;
  invoices: Locator;
  createInvoice: Locator;
  searchBusinessUnit: Locator;
  fu01UsBu01: Locator;
  supplier: Locator;
  number: Locator;
  amount: Locator;
  expandLines: Locator;
  amount2: Locator;
  searchDistributionSet: Locator;
  officeSupplies: Locator;
  searchPaymentTerms: Locator;
  immediate: Locator;
  invoiceActions: Locator;
  validate: Locator;
  saveAndClose: Locator;

  constructor(page: Page) {
    this.page = page;
    this.helper = new HelperClass(page);
    this.clickTheElementElement = page.locator(locators.clickTheElementElement);
    this.payables = page.locator(locators.payables);
    this.invoices = page.locator(locators.invoices);
    this.createInvoice = page.locator(locators.createInvoice);
    this.searchBusinessUnit = page.locator(locators.searchBusinessUnit);
    this.fu01UsBu01 = page.locator(locators.fu01UsBu01);
    this.supplier = page.locator(locators.supplier);
    this.number = page.locator(locators.number);
    this.amount = page.locator(locators.amount);
    this.expandLines = page.locator(locators.expandLines);
    this.amount2 = page.locator(locators.amount2);
    this.searchDistributionSet = page.locator(locators.searchDistributionSet);
    this.officeSupplies = page.locator(locators.officeSupplies);
    this.searchPaymentTerms = page.locator(locators.searchPaymentTerms);
    this.immediate = page.locator(locators.immediate);
    this.invoiceActions = page.locator(locators.invoiceActions);
    this.validate = page.locator(locators.validate);
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

  async setAmount(value: unknown): Promise<void> {
    const finalValue = this.coerceValue(value);
    await this.amount.fill(finalValue);
  }

  async setAmount2(value: unknown): Promise<void> {
    const finalValue = this.coerceValue(value);
    await this.amount2.fill(finalValue);
  }

  async applyData(formData: Record<string, any> | null | undefined, keys?: string[], index: number = 0): Promise<void> {
    const fallbackValues: Record<string, string> = {
      "Supplier": "",
      "Number": "",
      "Amount": "",
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
    if (shouldHandle("Amount")) {
      const value = this.resolveDataValue(formData, "Amount", fallbackValues["Amount"] ?? '');
      if (index === 0) {
        await this.setAmount(value);
      } else if (index === 1) {
        await this.setAmount2(value);
      }
    }
  }
}

export default Createinvoicepayablespage;
```

---

## REFERENCE TEST FILE (COPY EXCEL DATA BLOCK)

```typescript
import { test } from "./testSetup.ts";
import PageObject from "../pages/CreateinvoicepayablesPage.ts";
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

test.describe("Create_invoice_payables", () => {
  let createinvoicepayablespage: PageObject;

  const run = (name: string, fn: ({ page }, testinfo: any) => Promise<void>) =>
    (shouldRun(name) ? test : test.skip)(name, fn);

  run("Create_invoice_payables", async ({ page }, testinfo) => {
    createinvoicepayablespage = new PageObject(page);
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

    await namedStep("Step 1 - Click element", page, testinfo, async () => {
      await createinvoicepayablespage.clickTheElementElement.click();
      const screenshot = await page.screenshot();
      attachScreenshot("Step 1 - Click element", testinfo, screenshot);
    });

    await namedStep("Step 2 - Enter Supplier", page, testinfo, async () => {
      await createinvoicepayablespage.applyData(dataRow, ["Supplier"], 0);
      const screenshot = await page.screenshot();
      attachScreenshot("Step 2 - Enter Supplier", testinfo, screenshot);
    });

  });
});
```

---

## GENERATION RULES

1. **Page File Must Have**:
   - `import HelperClass from "../util/methods.utility.ts";`
   - `helper: HelperClass;` property
   - `this.helper = new HelperClass(page);` in constructor
   - ALL locator properties declared
   - ALL locators initialized in constructor
   - coerceValue, normaliseDataKey, resolveDataValue methods
   - Setter methods for input fields ONLY (supplier, number, amount, username, password, email, search)
   - applyData method

2. **Test File Must Have**:
   - Complete Excel data handling block (copy from reference)
   - namedStep for each action
   - Screenshot after each step
   - For inputs: `await pagename.applyData(dataRow, ["FieldName"], 0);`
   - For clicks: `await pagename.elementName.click();`

3. **Naming**:
   - Page class: `{Testname}page` (e.g., `Onecognizantpage`)
   - Variable: `{testname}page` (e.g., `onecognizantpage`)

Generate complete, working code. NO empty classes. NO generic methods. NO TODOs.
