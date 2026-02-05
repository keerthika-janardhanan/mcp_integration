# Example: LLM Test Generation

## INPUT TO LLM:

Generate Playwright test for login functionality:

**Test Name:** user-login
**Page Name:** LoginPage  
**URL:** https://app.example.com/login

**Steps:**
1. Enter username in field (xpath=//input[@id='username'])
2. Enter password in field (xpath=//input[@id='password'])
3. Click login button (xpath=//button[@id='loginBtn'])
4. Verify dashboard appears (xpath=//div[@id='dashboard'])

---

## EXPECTED OUTPUT FROM LLM:

### File 1: locators/user-login.ts
```typescript
const locators = {
  username: "xpath=//input[@id='username']",
  password: "xpath=//input[@id='password']",
  loginBtn: "xpath=//button[@id='loginBtn']",
  dashboard: "xpath=//div[@id='dashboard']",
};

export default locators;
```

### File 2: pages/LoginPage.ts
```typescript
import { Page, Locator } from '@playwright/test';
import HelperClass from "../util/methods.utility.ts";
import locators from "../locators/user-login.ts";

class LoginPage {
  page: Page;
  helper: HelperClass;
  username: Locator;
  password: Locator;
  loginBtn: Locator;
  dashboard: Locator;

  constructor(page: Page) {
    this.page = page;
    this.helper = new HelperClass(page);
    this.username = page.locator(locators.username);
    this.password = page.locator(locators.password);
    this.loginBtn = page.locator(locators.loginBtn);
    this.dashboard = page.locator(locators.dashboard);
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

  async setUsername(value: unknown): Promise<void> {
    const finalValue = this.coerceValue(value);
    await this.username.fill(finalValue);
  }

  async setPassword(value: unknown): Promise<void> {
    const finalValue = this.coerceValue(value);
    await this.password.fill(finalValue);
  }

  async applyData(formData: Record<string, any> | null | undefined, keys?: string[], index: number = 0): Promise<void> {
    const fallbackValues: Record<string, string> = {
      "Username": "",
      "Password": "",
    };
    const targetKeys = Array.isArray(keys) && keys.length ? keys.map((key) => this.normaliseDataKey(key)) : null;
    const shouldHandle = (key: string) => {
      if (!targetKeys) {
        return true;
      }
      return targetKeys.includes(this.normaliseDataKey(key));
    };
    if (shouldHandle("Username")) {
      await this.setUsername(this.resolveDataValue(formData, "Username", fallbackValues["Username"] ?? ''));
    }
    if (shouldHandle("Password")) {
      await this.setPassword(this.resolveDataValue(formData, "Password", fallbackValues["Password"] ?? ''));
    }
  }
}

export default LoginPage;
```

### File 3: tests/user-login.spec.ts
```typescript
import { test } from "./testSetup.ts";
import LoginPage from "../pages/LoginPage.ts";
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

test.describe("User_login", () => {
  let loginPage: LoginPage;

  const run = (name: string, fn: ({ page }, testinfo: any) => Promise<void>) =>
    (shouldRun(name) ? test : test.skip)(name, fn);

  run("User_login", async ({ page }, testinfo) => {
    loginPage = new LoginPage(page);
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

    await namedStep("Step 1 - Navigate to login page", page, testinfo, async () => {
      await page.goto("https://app.example.com/login");
      const screenshot = await page.screenshot();
      attachScreenshot("Step 1 - Navigate to login page", testinfo, screenshot);
    });

    await namedStep("Step 2 - Enter Username", page, testinfo, async () => {
      await loginPage.applyData(dataRow, ["Username"], 0);
      const screenshot = await page.screenshot();
      attachScreenshot("Step 2 - Enter Username", testinfo, screenshot);
    });

    await namedStep("Step 3 - Enter Password", page, testinfo, async () => {
      await loginPage.applyData(dataRow, ["Password"], 0);
      const screenshot = await page.screenshot();
      attachScreenshot("Step 3 - Enter Password", testinfo, screenshot);
    });

    await namedStep("Step 4 - Click login button", page, testinfo, async () => {
      await loginPage.loginBtn.click();
      const screenshot = await page.screenshot();
      attachScreenshot("Step 4 - Click login button", testinfo, screenshot);
    });

    await namedStep("Step 5 - Verify dashboard appears", page, testinfo, async () => {
      await loginPage.dashboard.waitFor({ state: 'visible' });
      const screenshot = await page.screenshot();
      attachScreenshot("Step 5 - Verify dashboard appears", testinfo, screenshot);
    });

  });
});
```

---

## Summary:
The LLM should generate all 3 files simultaneously, maintaining consistency across:
- Locator names
- Import paths
- Coding patterns
- Data handling logic
