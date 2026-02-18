# Test Data Setup Guide

## Overview
This guide explains how to properly configure test data for your Playwright test scripts. **All credentials and test data should come from Excel files, NOT from environment variables (.env files).**

## Problem Fixed
Previously, the system was incorrectly generating code that tried to read credentials from `process.env.USERNAME` and `process.env.PASSWORD`. This has been corrected - now all test data must come from Excel files in the `data/` folder.

## Test Data Flow

### 1. Excel File Structure
Test data should be stored in Excel files (.xlsx) in the `framework_repos/<repo>/data/` folder.

Example structure:
```
framework_repos/
  f870a1343bdd/
    data/
      LoginTestData.xlsx      ← Your test data file
      CreateInvoiceData.xlsx
```

### 2. Excel File Format
Each Excel file should contain:
- **Sheet Name**: Default sheet or custom sheet specified in `testmanager.xlsx`
- **ID Column**: A column containing unique test data IDs (e.g., "Id", "TestID")
- **Data Columns**: Columns matching the names used in `applyData()` calls

Example Excel content:
```
Id | Username | Password
---|----------|---------
1001 | testuser@example.com | TestPass123!
1002 | admin@example.com | AdminPass456!
```

#### Column Name Matching
The `applyData()` method uses flexible column name matching:

```typescript
// Test script calls:
await page.applyData(dataRow, ['username', 'Username', 'user'], 0);
await page.applyData(dataRow, ['password', 'Password', 'pass'], 0);

// This will match Excel columns named:
// - username (primary)
// - Username, user (case variations)
// - Any column that normalizes to the same key
```

**Recommended**: Use simple, consistent column names like `username` and `password` in your Excel files.

### 3. Test Manager Configuration
The `testmanager.xlsx` file controls which test data file to use for each test:

| TestCaseID              | DatasheetName          | ReferenceID | IDName  | SheetName |
|------------------------|------------------------|-------------|---------|-----------|
| Create_invoice_payables| CreateInvoiceData.xlsx | 1001        | Id      | Sheet1 |
| Testcase002            | workday.xlsx           | 1001        | Id      | Sheet1 |

### 4. Generated Code Usage

#### Page Class (applyData method)
```typescript
// pages/LoginPage.ts
async applyData(formData: Record<string, any> | null | undefined, keys?: string[], index: number = 0): Promise<void> {
  // Data values come from Excel files in ../data/ folder via formData parameter
  const fallbackValues: Record<string, string> = {
    "Username": "",  // Provide via Excel data file
    "Password": "",  // Provide via Excel data file
  };
  
  if (shouldHandle("Username")) {
    await this.setUsername(this.resolveDataValue(formData, "Username", fallbackValues["Username"] ?? ''));
  }
  if (shouldHandle("Password")) {
    await this.setPassword(this.resolveDataValue(formData, "Password", fallbackValues["Password"] ?? ''));
  }
}
```

#### Test File Usage
```typescript
// tests/login.spec.ts
test("User Login", async ({ page }, testinfo) => {
  const loginPage = new LoginPage(page);
  
  // Load data from Excel file based on testmanager.xlsx configuration
  const dataRow = readExcelData(dataSheetName, dataIdColumn, dataReferenceId, dataSheetTab);
  
  // Apply data from Excel file (NOT from process.env)
  await loginPage.applyData(dataRow, ["Username"], 0);
  await loginPage.applyData(dataRow, ["Password"], 0);
  
  // ❌ WRONG - Never use process.env for test data:
  // await loginPage.login(process.env.USERID, process.env.PASSWORD);
});
```

## Test Data Mapping Panel

After generating a script, the UI displays a "Test Data Mapping" panel showing:
- **Excel Column Name**: The column name expected in your Excel file
- **Action Type**: The type of action (fill, select, etc.)
- **Occurrences**: How many times this column is used
- **Methods Used**: Which methods use this data

This panel tells you exactly which columns you need in your Excel data file.

## Creating Test Data Files

### Step 1: Identify Required Columns
1. Generate your test script
2. Look at the "Test Data Mapping" panel
3. Note all the Excel column names listed

### Step 2: Create Excel File
1. Create a new Excel file (.xlsx) in `framework_repos/<repo>/data/`
2. Name it descriptively (e.g., `CreateSupplierData.xlsx`)
3. Create a sheet (e.g., "Sheet1")
4. Add an ID column (e.g., "SupplierID")
5. Add all required data columns from the Test Data Mapping panel
6. Add your test data rows with the ID and values

Example:
```
SupplierID | Supplier       | Number  | Amount
-----------|----------------|---------|--------
SUP001     | Acme Corp      | INV-123 | 5000.00
SUP002     | Widget Inc     | INV-124 | 7500.50
```

### Step 3: Update testmanager.xlsx
Add an entry for your test case:
```
TestCaseID           | DatasheetName              | ReferenceID | IDName     | SheetName
---------------------|----------------------------|-------------|------------|----------
Create_Supplier_Test | CreateSupplierData.xlsx    | SUP001      | SupplierID | Sheet1
```

### Step 4: Run Your Test
The test will automatically:
1. Read `testmanager.xlsx` to find the data file
2. Load `CreateSupplierData.xlsx`
3. Find the row where `SupplierID = "SUP001"`
4. Pass that row data to `applyData()` calls

## Environment Variables (REFERENCE_ID)

You can optionally override the `ReferenceID` at runtime:
```bash
# Run with specific test data row
REFERENCE_ID=SUP002 npx playwright test

# Or
DATA_REFERENCE_ID=SUP002 npx playwright test
```

This allows you to run the same test with different data without editing `testmanager.xlsx`.

## Common Issues

### Issue 1: "Test Data Mapping is Empty"
**Cause**: Test files don't contain `applyData()` calls
**Solution**: 
- Regenerate the script (the recent fix ensures proper generation)
- Ensure you're not using direct method calls like `login(process.env.USERID, process.env.PASSWORD)`
- Use `applyData()` pattern instead

### Issue 2: "No test data found" Error
**Cause**: Excel file doesn't exist or ReferenceID not found
**Solution**:
- Check that the Excel file exists in `data/` folder
- Verify the filename matches `DatasheetName` in `testmanager.xlsx`
- Ensure the ReferenceID exists in your Excel file
- Check the IDName column exists and matches

### Issue 3: Credentials Still Coming from .env
**Cause**: Using old generated scripts before the fix
**Solution**:
- Regenerate your scripts after the latest changes
- Remove any direct `process.env.USERID` or `process.env.PASSWORD` usage
- Replace with `applyData()` calls using Excel data

## Best Practices

1. **One Excel File Per Feature**: Keep related test data together
2. **Meaningful IDs**: Use descriptive IDs like "LOGIN_VALID_USER", not "001", "002"
3. **Column Name Consistency**: Use exact column names shown in Test Data Mapping panel
4. **Data Segregation**: Separate sensitive data appropriately (consider encryption for real credentials)
5. **Version Control**: Commit testmanager.xlsx and sample data files (use placeholder values for sensitive data)
6. **Documentation**: Add a README in your data/ folder explaining each Excel file's purpose

## Migration from process.env

If you have existing scripts using `process.env`:

1. **Identify environment variables used**:
   ```bash
   grep -r "process.env" framework_repos/*/tests/
   ```

2. **Create Excel columns** for each env var:
   - `process.env.USERID` → Excel column "Username" or "UserID"
   - `process.env.PASSWORD` → Excel column "Password"

3. **Replace in code**:
   ```typescript
   // Before:
   await loginPage.login(process.env.USERID, process.env.PASSWORD);
   
   // After:
   await loginPage.applyData(dataRow, ["Username"], 0);
   await loginPage.applyData(dataRow, ["Password"], 0);
   ```

4. **Regenerate scripts** using the updated system

## Recent Fixes Applied

### Issue 1: Test Data Mapping Empty
**Problem**: Test data mapping was empty because generated scripts didn't use `applyData()` calls with Excel data.
**Fix**: Updated LLM prompt to ensure all credentials come from Excel files, never from `process.env`.

### Issue 2: Trial Run Looking in Wrong Path  
**Problem**: Trial runs were looking for Excel files in the root framework directory instead of the `data/` subdirectory.
**Fix**: 
- Removed incorrect "brute force" data path modifications in trial adapter
- Fixed LLM prompt to use `dataFilePath` (full path) instead of `dataSheetName` (filename only) in `readExcelData()` calls
- Updated existing test files to use correct data paths

### Issue 3: Empty Data Directory
**Problem**: No sample Excel data files existed for testing.
**Solution**: Created sample `workday.xlsx` with required columns (Id, username, password) for Testcase002.

## Data Path Resolution

The system now correctly constructs data file paths:

```typescript
// ✅ CORRECT: Full path construction
const dataDir = path.join(__dirname, '../data');  // Resolves to ./data/
const dataFilePath = path.join(dataDir, dataSheetName);  // Full path to Excel file
const dataRow = readExcelData(dataFilePath, dataIdColumn, dataReferenceId, dataSheetTab);

// ❌ WRONG: Filename only (causes ENOENT errors)
const dataRow = readExcelData(dataSheetName, dataIdColumn, dataReferenceId, dataSheetTab);
```

## Testing the Fix

To test that the trial run now works correctly:

1. **Verify data file exists**:
   ```bash
   cd framework_repos/f870a1343bdd/data
   ls -la workday.xlsx
   ```

2. **Run trial**:
   ```bash
   # From the main project directory
   python -m app.executor run_trial_in_framework --script-path framework_repos/f870a1343bdd/tests/_last_trial_script.ts --framework-root framework_repos/f870a1343bdd
   ```

3. **Expected behavior**:
   - No more "ENOENT: no such file or directory" errors
   - Test data mapping panel shows populated columns
   - Trial run uses Excel data instead of environment variables
