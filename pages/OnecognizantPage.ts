import { Page, Locator } from '@playwright/test';
import HelperClass from "../util/methods.utility.ts";
import locators from "../locators/onecognizant.ts";

class Onecognizantpage {
  page: Page;
  helper: HelperClass;
  field1: Locator;
  field2: Locator;
  field3: Locator;
  field4: Locator;
  field5: Locator;
  button1: Locator;
  button2: Locator;

  constructor(page: Page) {
    this.page = page;
    this.helper = new HelperClass(page);
    this.field1 = page.locator(locators.field1);
    this.field2 = page.locator(locators.field2);
    this.field3 = page.locator(locators.field3);
    this.field4 = page.locator(locators.field4);
    this.field5 = page.locator(locators.field5);
    this.button1 = page.locator(locators.button1);
    this.button2 = page.locator(locators.button2);
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

  async setField1(value: unknown): Promise<void> {
    const finalValue = this.coerceValue(value);
    await this.field1.fill(finalValue);
  }

  async setField2(value: unknown): Promise<void> {
    const finalValue = this.coerceValue(value);
    await this.field2.fill(finalValue);
  }

  async setField3(value: unknown): Promise<void> {
    const finalValue = this.coerceValue(value);
    await this.field3.fill(finalValue);
  }

  async setField4(value: unknown): Promise<void> {
    const finalValue = this.coerceValue(value);
    await this.field4.fill(finalValue);
  }

  async setField5(value: unknown): Promise<void> {
    const finalValue = this.coerceValue(value);
    await this.field5.fill(finalValue);
  }

  async applyData(formData: Record<string, any> | null | undefined, keys?: string[], index: number = 0): Promise<void> {
    const fallbackValues: Record<string, string> = {
      "Field1": "",
      "Field2": "",
      "Field3": "",
      "Field4": "",
      "Field5": "",
    };
    const targetKeys = Array.isArray(keys) && keys.length ? keys.map((key) => this.normaliseDataKey(key)) : null;
    const shouldHandle = (key: string) => {
      if (!targetKeys) {
        return true;
      }
      return targetKeys.includes(this.normaliseDataKey(key));
    };
    if (shouldHandle("Field1")) {
      await this.setField1(this.resolveDataValue(formData, "Field1", fallbackValues["Field1"] ?? ''));
    }
    if (shouldHandle("Field2")) {
      await this.setField2(this.resolveDataValue(formData, "Field2", fallbackValues["Field2"] ?? ''));
    }
    if (shouldHandle("Field3")) {
      await this.setField3(this.resolveDataValue(formData, "Field3", fallbackValues["Field3"] ?? ''));
    }
    if (shouldHandle("Field4")) {
      await this.setField4(this.resolveDataValue(formData, "Field4", fallbackValues["Field4"] ?? ''));
    }
    if (shouldHandle("Field5")) {
      await this.setField5(this.resolveDataValue(formData, "Field5", fallbackValues["Field5"] ?? ''));
    }
  }
}

export default Onecognizantpage;
