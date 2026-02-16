# Fix: Excel Data Reading Error

## Error
```
TypeError: allData.find is not a function
```

## Root Cause
The `readExcelData()` function returns an object instead of an array, causing `.find()` to fail.

## Solution

### Option 1: Fix in Generated Test (Quick)

Edit the test file at line 58:

**Before:**
```typescript
const allData = readExcelData(dataSheetPath);
const foundRow = allData.find((row: any) => String(row[idName] ?? '').trim() === dataReferenceId);
```

**After:**
```typescript
const allData = readExcelData(dataSheetPath);
// Convert to array if it's an object
const dataArray = Array.isArray(allData) ? allData : Object.values(allData);
const foundRow = dataArray.find((row: any) => String(row[idName] ?? '').trim() === dataReferenceId);
```

### Option 2: Fix in Test Generator Template (Permanent)

Update the test generation template in `app/generators/agentic_script_agent.py`:

Find the Excel data reading section and replace with:

```typescript
// Read test data from Excel
let dataRow: any = {};
if (fs.existsSync(dataSheetPath)) {
  const allData = readExcelData(dataSheetPath);
  // Ensure allData is an array
  const dataArray = Array.isArray(allData) ? allData : Object.values(allData);
  const foundRow = dataArray.find((row: any) => String(row[idName] ?? '').trim() === dataReferenceId);
  if (foundRow) {
    dataRow = foundRow;
  }
}
```

### Option 3: Fix readExcelData() Function

If you have access to the Excel utility file, ensure it returns an array:

```typescript
export function readExcelData(filePath: string): any[] {
  const workbook = XLSX.readFile(filePath);
  const sheetName = workbook.SheetNames[0];
  const worksheet = workbook.Sheets[sheetName];
  const data = XLSX.utils.sheet_to_json(worksheet);
  
  // Ensure it's always an array
  return Array.isArray(data) ? data : [];
}
```

## Quick Command to Fix Current Test

```powershell
# Navigate to the test file
cd C:\Users\2218532\PycharmProjects\mcp_integration\framework_repos\f870a1343bdd

# Edit tests/tmpm6b6xjoj.spec.ts at line 58
# Replace the line with the fixed version above
```

## Prevent Future Issues

Add this to your test generation prompt:

```
When reading Excel data, always ensure the result is an array:
const dataArray = Array.isArray(allData) ? allData : Object.values(allData);
```

## Re-run Test

After fixing:

```powershell
cd C:\Users\2218532\PycharmProjects\mcp_integration\framework_repos\f870a1343bdd
npx playwright test tests/tmpm6b6xjoj.spec.ts --headed
```
