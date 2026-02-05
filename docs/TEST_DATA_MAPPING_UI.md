# Test Data Mapping UI Feature

## Overview
This feature exposes the **expected Excel column headers** from generated Playwright scripts to the UI, allowing users to prepare their test data correctly.

## What It Does
When a test script is generated, the `applyData()` method in the Page Object expects specific Excel column names (e.g., "Business Unit", "Supplier"). This feature displays these mappings to users so they know exactly what columns to create in their Excel test data files.

## Backend Changes

### 1. `app/agentic_script_agent.py`
**Added:** Test data mapping extraction in `_build_deterministic_payload()`

```python
# Build test data mapping for UI display
test_data_mapping = []
for data_key in sorted(fallback_map.keys()):
    bindings_for_key = [b for b in data_bindings if b['data_key'] == data_key]
    occurrences = len(bindings_for_key)
    action_types = list({b['action_category'] for b in bindings_for_key})
    test_data_mapping.append({
        'columnName': data_key,
        'occurrences': occurrences,
        'actionType': action_types[0] if len(action_types) == 1 else 'mixed',
        'methods': [b['method_name'] for b in bindings_for_key]
    })

return {
    'locators': [...],
    'pages': [...],
    'tests': [...],
    'testDataMapping': test_data_mapping,  # NEW
}
```

**What it captures:**
- `columnName`: Excel column header expected (e.g., "Business Unit")
- `occurrences`: How many times this field appears (e.g., 2 if used for header and line item)
- `actionType`: `fill` (text input), `select` (dropdown), or `mixed`
- `methods`: Which Page Object methods handle this field (e.g., `setBusinessUnit`, `selectSupplier`)

### 2. `app/api/routers/agentic.py`
**Added:** `TestDataMapping` model and updated response

```python
class TestDataMapping(BaseModel):
    columnName: str
    occurrences: int
    actionType: str
    methods: list[str]

class PayloadResponse(BaseModel):
    locators: list[FileItem]
    pages: list[FileItem]
    tests: list[FileItem]
    testDataMapping: list[TestDataMapping]  # NEW
```

**Endpoint updated:** `/agentic/payload` now returns `testDataMapping` array

### 3. Frontend API (`frontend/src/api/agentic.ts`)
**Added:** TypeScript interface

```typescript
export interface TestDataMapping {
  columnName: string;
  occurrences: number;
  actionType: string;
  methods: string[];
}
```

## Frontend Changes

### `frontend/src/pages/HorizontalFlowLayout.tsx`

**Added state:**
```typescript
const [testDataMapping, setTestDataMapping] = useState<any[]>([]);
```

**Store mapping on script generation:**
```typescript
const data = await generatePayload(scenario, editableFlowPreview);
setTestDataMapping(data.testDataMapping || []);
```

**UI Display:** Added table in "Generated Test Script" step showing:
- Excel column name (e.g., "Business Unit")
- Action type badge (fill/select/mixed)
- Number of occurrences

## User Experience

### Before
User generates script → gets TypeScript code → manually inspects `applyData()` to figure out column names → creates Excel with correct headers

### After
User generates script → sees **Test Data Mapping table** showing:
```
Excel Column Name    Action Type    Occurrences
─────────────────    ───────────    ───────────
Business Unit        fill           1x
Supplier            select          1x
Amount              fill            2x
```
→ creates Excel with these exact column headers → script works immediately

## Example Payload Response

```json
{
  "locators": [...],
  "pages": [...],
  "tests": [...],
  "testDataMapping": [
    {
      "columnName": "Business Unit",
      "occurrences": 1,
      "actionType": "fill",
      "methods": ["setBusinessUnit"]
    },
    {
      "columnName": "Supplier",
      "occurrences": 1,
      "actionType": "select",
      "methods": ["selectSupplier"]
    }
  ]
}
```

## Integration Points

1. **Recorder → Vector DB → Agent:**
   - Recorder captures `data` field from UI interactions
   - Ingested into vector DB with `data_key` metadata
   - Agent reads `data_key` during script generation
   - `data_bindings` list tracks all field mappings

2. **Agent → API → Frontend:**
   - `_build_deterministic_payload` constructs mapping
   - `/agentic/payload` endpoint returns it
   - React UI displays in table format

3. **User workflow:**
   - Record flow with data entry
   - Generate preview → confirm
   - Generate script → **see test data mapping table**
   - Create Excel with matching columns
   - Upload to TestManager → run tests

## Related Documentation
- See `docs/TEST_DATA_FIELD_TYPE_GUIDE.md` for Excel column header conventions (dropdown/common suffixes)
- See `docs/RECORDER_TO_SCRIPT_FLOW.md` for complete recorder→script pipeline

## Testing
To verify this feature:
1. Start backend: `python -m uvicorn app.api.main:app --host 127.0.0.1 --port 8001 --reload`
2. Start frontend: `cd frontend; npm run dev` (port 5178)
3. Record a flow with data entry (Business Unit, Supplier, etc.)
4. Generate script via UI
5. Check "Generated Test Script" section for **Test Data Mapping** table
6. Verify Excel column names match what's displayed

## Future Enhancements
- Export mapping as CSV for easy Excel template creation
- Highlight required vs optional fields
- Show example values from recording
- Link to field type guide (dropdown/common syntax)
