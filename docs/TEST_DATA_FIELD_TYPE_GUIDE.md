# Test Data Field Type Handling

## Problem
Excel test data has mixed field types:
- **Fill fields**: direct text input (Number, Amount)
- **Dropdown fields**: autocomplete/select (Supplier, Region)
- **Common fields**: reference data not directly entered (Status, ID)

## Solution: Column Header Conventions

### Format
Use parentheses in Excel column headers to specify field type:

```
Invoice ID | Supplier (dropdown) | Number | Amount | Region (dropdown) | Notes (common)
10001      | TEST_Sup_001       | CM-123 | 100    | APAC             | Test invoice
```

### Field Type Rules
- **(dropdown)**: Triggers `applyData` + dynamic option click
- **(common)**: Available in `dataRow` but no auto-fill
- **No suffix**: Treated as fill field by default

## Implementation Steps

### 1. Update Excel Helper to Parse Field Types

**File:** `framework_repos/.../util/csvFileManipulation.ts`

Add field type metadata extraction:

```typescript
export interface FieldMetadata {
  columnName: string;
  fieldType: 'fill' | 'dropdown' | 'common';
  cleanName: string; // Without (dropdown) suffix
}

export function parseFieldMetadata(headers: string[]): FieldMetadata[] {
  return headers.map(header => {
    const dropdownMatch = header.match(/^(.+?)\s*\(dropdown\)$/i);
    const commonMatch = header.match(/^(.+?)\s*\(common\)$/i);
    
    if (dropdownMatch) {
      return { columnName: header, fieldType: 'dropdown', cleanName: dropdownMatch[1].trim() };
    }
    if (commonMatch) {
      return { columnName: header, fieldType: 'common', cleanName: commonMatch[1].trim() };
    }
    return { columnName: header, fieldType: 'fill', cleanName: header.trim() };
  });
}
```

### 2. Update Page Object applyData Method

Add field type awareness:

```typescript
async applyData(
  formData: Record<string, any>,
  keys?: string[],
  fieldMetadata?: FieldMetadata[]
): Promise<void> {
  for (const key of keys || Object.keys(formData)) {
    const meta = fieldMetadata?.find(m => 
      this.normaliseDataKey(m.cleanName) === this.normaliseDataKey(key)
    );
    
    if (meta?.fieldType === 'common') {
      continue; // Skip common fields
    }
    
    const value = this.resolveDataValue(formData, key);
    
    if (meta?.fieldType === 'dropdown') {
      // Fill then wait for dropdown options
      await this[`set${key}`](value);
      await this.page.waitForTimeout(500); // Allow dropdown to populate
    } else {
      await this[`set${key}`](value);
    }
  }
}
```

### 3. Update Test Spec to Pass Metadata

```typescript
const fieldMetadata = parseFieldMetadata(Object.keys(dataRow));
await payablesPage.applyData(dataRow, ['Supplier', 'Number'], fieldMetadata);
```

## Alternative: Auto-Detection from Recorder

Update `app/metadata_utils.py` to tag field types during recording:

```python
def infer_field_type(element: Dict) -> str:
    role = element.get('role', '').lower()
    tag = element.get('tag', '').lower()
    
    if role == 'combobox' or 'select' in tag:
        return 'dropdown'
    if role in ('textbox', 'spinbutton') or tag == 'input':
        return 'fill'
    return 'common'
```

Store in refined steps:
```json
{
  "data_key": "Supplier",
  "field_type": "dropdown",
  "action": "Fill"
}
```

Then generator reads `field_type` from vector steps to produce appropriate code.

## Recommended Approach

**Use Column Header Conventions** — simpler, no recorder changes needed, and testers can control field types directly in Excel.
