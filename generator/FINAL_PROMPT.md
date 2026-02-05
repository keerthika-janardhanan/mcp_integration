# TEST SCRIPT GENERATOR PROMPT

When generating Playwright test scripts, you MUST generate 3 files. Use this EXACT template structure:

---

## REFERENCE TEMPLATE (COPY THIS STRUCTURE EXACTLY)

### File 1: locators/{test-name}.ts
```typescript
const locators = {
  clickTheElementElement: "xpath=//*[@id=\"pt1:_UISmmLink::icon\"]",
  payables: "xpath=//*[@id=\"pt1:_UISnvr:0:nvgpgl2_groupNode_payables\"]",
  supplier: "xpath=//*[@id=\"_FOpt1:_FOr1:0:_FONSr2:0:MAnt2:1:pm1:r1:0:ap1:r2:0:ic3::content\"]",
};

export default locators;
```

### File 2: pages/{Pagename}page.ts
```typescript
import { Page, Locator } from '@playwright/test';
import HelperClass from "../util/methods.utility.ts";
import locators from "../locators/{test-name}.ts";

class {Pagename}page {
  page: Page;
  helper: HelperClass;
  clickTheElementElement: Locator;
  payables: Locator;
  supplier: Locator;

  constructor(page: Page) {
    this.page = page;
    this.helper = new HelperClass(page);
    this.clickTheElementElement = page.locator(locators.clickTheElementElement);
    this.payables = page.locator(locators.payables);
    this.supplier = page.locator(locators.supplier);
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

  async applyData(formData: Record<string, any> | null | undefined, keys?: string[], index: number = 0): Promise<void> {
    const fallbackValues: Record<string, string> = {
      "Supplier": "",
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
  }
}

export default {Pagename}page;
```

---

## MANDATORY RULES

1. **ALWAYS include in page file**:
   - `import HelperClass from "../util/methods.utility.ts";`
   - `helper: HelperClass;` property
   - `this.helper = new HelperClass(page);` in constructor
   - ALL locator properties (one for each locator)
   - ALL locator initializations in constructor
   - ALL 3 private methods: coerceValue, normaliseDataKey, resolveDataValue
   - Setter methods for input fields ONLY
   - applyData method

2. **Create setter methods ONLY for**:
   - Fields with names like: supplier, number, amount, username, password, email, search, text, input
   - DO NOT create setters for: buttons, links, clicks, actions, validate, close, expand, icons, cells

3. **Naming**:
   - Test file: `tests/test-name.spec.ts` (kebab-case)
   - Locator file: `locators/test-name.ts` (kebab-case)
   - Page file: `pages/Testnamepage.ts` (PascalCase + lowercase 'page')
   - Class name: `Testnamepage` (PascalCase + lowercase 'page')

4. **NEVER generate**:
   - Empty page classes
   - Generic methods like fillElement() or clickElement()
   - Missing locator properties
   - Missing helper property

---

## STEP-BY-STEP GENERATION

Given user input with UI interactions:

**Step 1**: Create locators file
- Extract all element selectors
- Use camelCase names
- Prefix with `xpath=`

**Step 2**: Create page file
- Copy the template structure EXACTLY
- Replace {Pagename} with actual page name
- Replace {test-name} with actual test name
- Add ALL locator properties from Step 1
- Initialize ALL locators in constructor
- Create setter methods for input fields only
- Update applyData with all input fields

**Step 3**: Create test file
- Use standard test template with Excel data handling
- Use namedStep for each action
- For inputs: `await pagename.applyData(dataRow, ["FieldName"], 0);`
- For clicks: `await pagename.elementName.click();`

---

## EXAMPLE

**Input**: Test "user-login" with username field, password field, login button

**Output**:

### locators/user-login.ts
```typescript
const locators = {
  username: "xpath=//input[@id='user']",
  password: "xpath=//input[@id='pass']",
  loginButton: "xpath=//button[@id='login']",
};

export default locators;
```

### pages/Userloginpage.ts
```typescript
import { Page, Locator } from '@playwright/test';
import HelperClass from "../util/methods.utility.ts";
import locators from "../locators/user-login.ts";

class Userloginpage {
  page: Page;
  helper: HelperClass;
  username: Locator;
  password: Locator;
  loginButton: Locator;

  constructor(page: Page) {
    this.page = page;
    this.helper = new HelperClass(page);
    this.username = page.locator(locators.username);
    this.password = page.locator(locators.password);
    this.loginButton = page.locator(locators.loginButton);
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

export default Userloginpage;
```

Note: loginButton does NOT get a setter method because it's a button (click only).

---

Now generate the 3 files based on user input.
