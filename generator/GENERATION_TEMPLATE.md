## Test Script Generation Prompt Template

When generating Playwright test scripts, follow this structure:

### Input Required:
1. Test name (e.g., "create-invoice-payables")
2. Page name (e.g., "CreateinvoicepayablesPage")
3. List of UI interactions with selectors

### Output Structure:

Generate 3 files:

#### 1. locators/{test-name}.ts
```typescript
const locators = {
  elementName: "xpath=//selector",
  // ... more locators
};

export default locators;
```

#### 2. pages/{PageName}.ts
```typescript
import { Page, Locator } from '@playwright/test';
import HelperClass from "../util/methods.utility.ts";
import locators from "../locators/{test-name}.ts";

class {PageName} {
  page: Page;
  helper: HelperClass;
  // Declare all locators as properties
  
  constructor(page: Page) {
    this.page = page;
    this.helper = new HelperClass(page);
    // Initialize all locators
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

  // Setter methods for input fields only
  async setFieldName(value: unknown): Promise<void> {
    const finalValue = this.coerceValue(value);
    await this.fieldName.fill(finalValue);
  }

  // applyData method for data-driven testing
  async applyData(formData: Record<string, any> | null | undefined, keys?: string[], index: number = 0): Promise<void> {
    // Implementation
  }
}

export default {PageName};
```

#### 3. tests/{test-name}.spec.ts
```typescript
import { test } from "./testSetup.ts";
import {PageName} from "../pages/{PageName}.ts";
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

test.describe("{TestName}", () => {
  let {pageVarName}: {PageName};

  const run = (name: string, fn: ({ page }, testinfo: any) => Promise<void>) =>
    (shouldRun(name) ? test : test.skip)(name, fn);

  run("{TestName}", async ({ page }, testinfo) => {
    {pageVarName} = new {PageName}(page);
    // Excel data handling logic
    // Test steps with namedStep and screenshots
  });
});
```

### Rules:
1. Input fields (text, number, search) get setter methods
2. Clickable elements (buttons, links) only get locator declarations
3. All steps wrapped in namedStep with screenshots
4. Excel data integration with applyData method
5. Proper error handling for missing data files
