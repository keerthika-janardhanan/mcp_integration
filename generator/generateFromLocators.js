const fs = require('fs');
const path = require('path');
const { generatePageClass, generateTestSpec } = require('./codeGenerator');

const locatorFilePath = process.argv[2];
const pageName = process.argv[3];
const testName = process.argv[4];

if (!locatorFilePath || !pageName || !testName) {
  console.log('Usage: node generateFromLocators.js <locator-file-path> <PageName> <test-name>');
  console.log('Example: node generateFromLocators.js ../locators/onecognizant.ts OnecognizantPage onecognizant-test');
  process.exit(1);
}

const absoluteLocatorPath = path.resolve(locatorFilePath);
const locatorFileName = path.basename(locatorFilePath, '.ts');

delete require.cache[require.resolve(absoluteLocatorPath)];
const locatorsModule = require(absoluteLocatorPath);
const locators = locatorsModule.default || locatorsModule;

const pageCode = generatePageClass(pageName, locators, locatorFileName);
const testCode = generateTestSpec(testName, pageName, locators);

const projectRoot = path.resolve(__dirname, '..');
const pagesDir = path.join(projectRoot, 'pages');
const testsDir = path.join(projectRoot, 'tests');

if (!fs.existsSync(pagesDir)) {
  fs.mkdirSync(pagesDir, { recursive: true });
}
if (!fs.existsSync(testsDir)) {
  fs.mkdirSync(testsDir, { recursive: true });
}

const pageFilePath = path.join(pagesDir, `${pageName}.ts`);
const testFilePath = path.join(testsDir, `${testName}.spec.ts`);

fs.writeFileSync(pageFilePath, pageCode);
fs.writeFileSync(testFilePath, testCode);

console.log(`✓ Generated: ${pageFilePath}`);
console.log(`✓ Generated: ${testFilePath}`);
