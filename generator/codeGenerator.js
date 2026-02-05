const fs = require('fs');
const path = require('path');

function generatePageClass(pageName, locatorsObj, locatorFileName) {
  const locatorKeys = Object.keys(locatorsObj);
  const inputFields = locatorKeys.filter(key => {
    const lower = key.toLowerCase();
    return !lower.includes('click') && !lower.includes('button') && 
           !lower.includes('link') && !lower.includes('cell') && 
           !lower.includes('actions') && !lower.includes('validate') && 
           !lower.includes('close') && !lower.includes('expand') &&
           !lower.includes('element') && !lower.includes('icon');
  });

  let code = `import { Page, Locator } from '@playwright/test';
import HelperClass from "../util/methods.utility.ts";
import locators from "../locators/${locatorFileName}.ts";

class ${pageName} {
  page: Page;
  helper: HelperClass;
`;

  locatorKeys.forEach(key => {
    code += `  ${key}: Locator;\n`;
  });

  code += `
  constructor(page: Page) {
    this.page = page;
    this.helper = new HelperClass(page);
`;

  locatorKeys.forEach(key => {
    code += `    this.${key} = page.locator(locators.${key});\n`;
  });

  code += `  }

  private coerceValue(value: unknown): string {
    if (value === undefined || value === null) {
      return '';
    }
    if (typeof value === 'number') {
      return \`\${value}\`;
    }
    if (typeof value === 'string') {
      return value;
    }
    return \`\${value ?? ''}\`;
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
`;

  inputFields.forEach(field => {
    const methodName = `set${field.charAt(0).toUpperCase()}${field.slice(1)}`;
    code += `
  async ${methodName}(value: unknown): Promise<void> {
    const finalValue = this.coerceValue(value);
    await this.${field}.fill(finalValue);
  }
`;
  });

  if (inputFields.length > 0) {
    code += `
  async applyData(formData: Record<string, any> | null | undefined, keys?: string[], index: number = 0): Promise<void> {
    const fallbackValues: Record<string, string> = {
`;
    inputFields.forEach(field => {
      const displayName = field.charAt(0).toUpperCase() + field.slice(1);
      code += `      "${displayName}": "",\n`;
    });
    code += `    };
    const targetKeys = Array.isArray(keys) && keys.length ? keys.map((key) => this.normaliseDataKey(key)) : null;
    const shouldHandle = (key: string) => {
      if (!targetKeys) {
        return true;
      }
      return targetKeys.includes(this.normaliseDataKey(key));
    };
`;

    inputFields.forEach(field => {
      const displayName = field.charAt(0).toUpperCase() + field.slice(1);
      const methodName = `set${displayName}`;
      code += `    if (shouldHandle("${displayName}")) {
      await this.${methodName}(this.resolveDataValue(formData, "${displayName}", fallbackValues["${displayName}"] ?? ''));
    }
`;
    });

    code += `  }\n`;
  }

  code += `}

export default ${pageName};
`;

  return code;
}

function generateTestSpec(testName, pageName, locatorsObj) {
  const locatorKeys = Object.keys(locatorsObj);
  const inputFields = locatorKeys.filter(key => {
    const lower = key.toLowerCase();
    return !lower.includes('click') && !lower.includes('button') && 
           !lower.includes('link') && !lower.includes('cell') && 
           !lower.includes('actions') && !lower.includes('validate') && 
           !lower.includes('close') && !lower.includes('expand') &&
           !lower.includes('element') && !lower.includes('icon');
  });

  const pageVarName = `${pageName.charAt(0).toLowerCase()}${pageName.slice(1)}`;

  let code = `import { test } from "./testSetup.ts";
import ${pageName} from "../pages/${pageName}.ts";
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

test.describe("${testName}", () => {
  let ${pageVarName}: ${pageName};

  const run = (name: string, fn: ({ page }, testinfo: any) => Promise<void>) =>
    (shouldRun(name) ? test : test.skip)(name, fn);

  run("${testName}", async ({ page }, testinfo) => {
    ${pageVarName} = new ${pageName}(page);
    const testCaseId = testinfo.title;
    const testRow: Record<string, any> = executionList?.find((row: any) => row['TestCaseID'] === testCaseId) ?? {};
    const defaultDataStem = (() => {
      const core = testCaseId.replace(/[^a-z0-9]+/gi, ' ').trim();
      if (!core) {
        return 'TestData';
      }
      return core.split(/\\s+/).map((part) => part.charAt(0).toUpperCase() + part.slice(1)).join('');
    })();
    const defaultDatasheetName = \`\${defaultDataStem}Data.xlsx\`;
    const defaultIdColumn = \`\${defaultDataStem}ID\`;
    const defaultReferenceId = \`\${defaultDataStem}001\`;
    const dataSheetName = String(testRow?.['DatasheetName'] ?? '').trim() || defaultDatasheetName;
    const envReferenceId = (process.env.REFERENCE_ID || process.env.DATA_REFERENCE_ID || '').trim();
    const excelReferenceId = String(testRow?.['ReferenceID'] ?? '').trim() || defaultReferenceId;
    const dataReferenceId = envReferenceId || excelReferenceId;
    console.log(\`[ReferenceID] Using: \${dataReferenceId} (source: \${envReferenceId ? 'env' : 'excel'})\`);
    const dataIdColumn = String(testRow?.['IDName'] ?? '').trim() || defaultIdColumn;
    const dataSheetTab = String(testRow?.['SheetName'] ?? testRow?.['Sheet'] ?? '').trim();
    const dataDir = path.join(__dirname, '../data');
    fs.mkdirSync(dataDir, { recursive: true });
    let dataRow: Record<string, any> = {};
    const ensureDataFile = (): string | null => {
      if (!dataSheetName) {
        console.warn(\`[DATA] DatasheetName missing for \${testCaseId}; using generated defaults.\`);
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
            console.warn(\`[DATA] Unable to scan data directory for \${dataSheetName}:\`, err);
            return null;
          }
        })();
        if (caseInsensitiveMatch) {
          return caseInsensitiveMatch;
        }
        const message = \`Test data file '\${dataSheetName}' not found in data/. Upload the file before running '\${testCaseId}'.\`;
        console.warn(\`[DATA] \${message}\`);
        throw new Error(message);
      }
      return expectedPath;
    };
    const dataPath = ensureDataFile();
    if (dataPath && dataReferenceId && dataIdColumn) {
      dataRow = readExcelData(dataPath, dataSheetTab || '', dataReferenceId, dataIdColumn) ?? {};
      if (!dataRow || Object.keys(dataRow).length === 0) {
        console.warn(\`[DATA] Row not found in \${dataSheetName} for \${dataIdColumn}='\${dataReferenceId}'.\`);
      }
    } else if (dataSheetName) {
      console.warn(\`[DATA] DatasheetName provided but ReferenceID/IDName missing for \${testCaseId}. Generated defaults will be used.\`);
    }

`;

  let stepNumber = 0;
  locatorKeys.forEach(key => {
    stepNumber++;
    const isInput = inputFields.includes(key);
    const displayName = key.replace(/([A-Z])/g, ' $1').trim();
    
    if (isInput) {
      const fieldKey = key.charAt(0).toUpperCase() + key.slice(1);
      code += `    await namedStep("Step ${stepNumber} - Enter ${displayName}", page, testinfo, async () => {
      await ${pageVarName}.applyData(dataRow, ["${fieldKey}"], 0);
      const screenshot = await page.screenshot();
      attachScreenshot("Step ${stepNumber} - Enter ${displayName}", testinfo, screenshot);
    });

`;
    } else {
      code += `    await namedStep("Step ${stepNumber} - Click ${displayName}", page, testinfo, async () => {
      await ${pageVarName}.${key}.click();
      const screenshot = await page.screenshot();
      attachScreenshot("Step ${stepNumber} - Click ${displayName}", testinfo, screenshot);
    });

`;
    }
  });

  code += `  });
});
`;

  return code;
}

module.exports = { generatePageClass, generateTestSpec };
