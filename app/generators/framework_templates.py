"""
Template-based framework code generation with LLM enhancement
Uses predefined templates enhanced by LLM analysis of framework repository
for reusable code detection, coding standards, and dynamic element handling
"""
from __future__ import annotations

import json
import re
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

TEMPLATE_DIR = Path(__file__).parent.parent.parent / "templates"

logger = logging.getLogger(__name__)


class FrameworkTemplate:
    """Manages framework templates and generates code from them"""
    
    @staticmethod
    def load_template(template_name: str) -> str:
        """Load a template file"""
        template_path = TEMPLATE_DIR / template_name
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_name}")
        return template_path.read_text(encoding='utf-8')
    
    @staticmethod
    def to_pascal_case(text: str) -> str:
        """Convert text to PascalCase for class names"""
        # Remove special characters and split on spaces/underscores
        words = re.sub(r'[^\w\s]', '', text).split()
        return ''.join(word.capitalize() for word in words)
    
    @staticmethod
    def to_snake_case(text: str) -> str:
        """Convert text to snake_case for file names"""
        # Replace spaces and special chars with underscores
        text = re.sub(r'[^\w\s-]', '', text).strip().lower()
        return re.sub(r'[-\s]+', '_', text)
    
    @classmethod
    def generate_locator_file(cls, flow_name: str, locators: List[Dict[str, Any]]) -> str:
        """Generate locators file from template"""
        template = cls.load_template("playwright_locator.ts.template")
        
        class_name = cls.to_pascal_case(flow_name)
        
        # Generate locator definitions
        locator_defs = []
        for idx, loc in enumerate(locators, 1):
            locator_name = f"step{idx}Element"
            playwright_loc = loc.get('playwright', '')
            css_loc = loc.get('css', '')
            xpath_loc = loc.get('xpath', '')
            
            # Priority: playwright > css > xpath
            if playwright_loc:
                selector = f"this.page.{playwright_loc}"
            elif css_loc:
                selector = f"this.page.locator('{css_loc}')"
            elif xpath_loc:
                selector = f"this.page.locator('xpath={xpath_loc}')"
            else:
                continue
            
            locator_defs.append(f"  get {locator_name}() {{ return {selector}; }}")
        
        locator_definitions = '\n'.join(locator_defs)
        
        return template.replace('{{FLOW_NAME}}', flow_name) \
                      .replace('{{GENERATED_DATE}}', datetime.now().strftime('%Y-%m-%d %H:%M:%S')) \
                      .replace('{{CLASS_NAME}}', class_name) \
                      .replace('{{LOCATOR_DEFINITIONS}}', locator_definitions)
    
    @classmethod
    def generate_page_file(cls, flow_name: str, steps: List[Dict[str, Any]]) -> str:
        """Generate page object file from template"""
        template = cls.load_template("playwright_page.ts.template")
        
        class_name = cls.to_pascal_case(flow_name)
        file_name = cls.to_snake_case(flow_name)
        
        # Generate page methods
        page_methods = []
        for idx, step in enumerate(steps, 1):
            action = step.get('action', 'click').lower()
            navigation = step.get('navigation', f'Step {idx}')
            method_name = f"step{idx}_{action}"
            
            if action in ['fill', 'type', 'input']:
                page_methods.append(f"""
  async {method_name}(value: string) {{
    // {navigation}
    await this.locators.step{idx}Element.fill(value);
  }}""")
            elif action == 'click':
                page_methods.append(f"""
  async {method_name}() {{
    // {navigation}
    await this.locators.step{idx}Element.click();
  }}""")
            elif action == 'select':
                page_methods.append(f"""
  async {method_name}(option: string) {{
    // {navigation}
    await this.locators.step{idx}Element.selectOption(option);
  }}""")
        
        page_method_code = '\n'.join(page_methods)
        
        return template.replace('{{FLOW_NAME}}', flow_name) \
                      .replace('{{GENERATED_DATE}}', datetime.now().strftime('%Y-%m-%d %H:%M:%S')) \
                      .replace('{{CLASS_NAME}}', class_name) \
                      .replace('{{FILE_NAME}}', file_name) \
                      .replace('{{PAGE_METHODS}}', page_method_code)
    
    @classmethod
    def generate_test_file(cls, flow_name: str, steps: List[Dict[str, Any]], start_url: str = '') -> str:
        """Generate test spec file from template"""
        template = cls.load_template("playwright_test.spec.ts.template")
        
        class_name = cls.to_pascal_case(flow_name)
        file_name = cls.to_snake_case(flow_name)
        
        # Generate test case
        test_steps = []
        if start_url:
            test_steps.append(f"    await page.navigate('{start_url}');")
        
        for idx, step in enumerate(steps, 1):
            action = step.get('action', 'click').lower()
            data = step.get('data', '')
            expected = step.get('expected', '')
            
            if action in ['fill', 'type', 'input'] and data:
                test_steps.append(f"    await page.step{idx}_{action}('{data}');")
            elif action == 'click':
                test_steps.append(f"    await page.step{idx}_{action}();")
            elif action == 'select' and data:
                test_steps.append(f"    await page.step{idx}_{action}('{data}');")
            
            if expected:
                test_steps.append(f"    // Expected: {expected}")
        
        test_case = f"""
  test('{flow_name} - Happy Path', async () => {{
{chr(10).join(test_steps)}
  }});"""
        
        return template.replace('{{FLOW_NAME}}', flow_name) \
                      .replace('{{GENERATED_DATE}}', datetime.now().strftime('%Y-%m-%d %H:%M:%S')) \
                      .replace('{{CLASS_NAME}}', class_name) \
                      .replace('{{FILE_NAME}}', file_name) \
                      .replace('{{TEST_CASES}}', test_case)
    
    @classmethod
    def generate_test_data_mapping(cls, flow_name: str, steps: List[Dict[str, Any]], scenario: str = '') -> str:
        """Generate test data mapping JSON from template"""
        template = cls.load_template("test_data_mapping.json.template")
        
        # Extract fields from steps
        fields = []
        for idx, step in enumerate(steps, 1):
            action = step.get('action', '').lower()
            navigation = step.get('navigation', f'Step {idx}')
            data = step.get('data', '')
            
            if action in ['fill', 'type', 'input', 'select']:
                locators = step.get('locators', {})
                field_name = locators.get('name', '') or locators.get('label', '') or f"field_{idx}"
                
                fields.append({
                    "fieldName": field_name,
                    "step": idx,
                    "action": action,
                    "description": navigation,
                    "sampleValue": data if data else "{{TO_BE_PROVIDED}}",
                    "required": True,
                    "dataType": "string"
                })
        
        # Convert fields to properly formatted JSON array elements
        if fields:
            test_data_fields = ',\n        '.join(json.dumps(field) for field in fields)
        else:
            test_data_fields = ''
        
        return template.replace('{{FLOW_NAME}}', flow_name) \
                      .replace('{{GENERATED_DATE}}', datetime.now().strftime('%Y-%m-%d %H:%M:%S')) \
                      .replace('{{SCENARIO}}', scenario or flow_name) \
                      .replace('{{TEST_DATA_FIELDS}}', test_data_fields)
    
    @classmethod
    def generate_all_files(cls, flow_name: str, steps: List[Dict[str, Any]], start_url: str = '', scenario: str = '') -> Dict[str, str]:
        """Generate all framework files from templates (static - no LLM)"""
        file_name = cls.to_snake_case(flow_name)
        
        # Extract locators from steps
        locators = [step.get('locators', {}) for step in steps]
        
        return {
            f"locators/{file_name}.locators.ts": cls.generate_locator_file(flow_name, locators),
            f"pages/{file_name}.page.ts": cls.generate_page_file(flow_name, steps),
            f"tests/{file_name}.spec.ts": cls.generate_test_file(flow_name, steps, start_url),
            f"data/{file_name}_data.json": cls.generate_test_data_mapping(flow_name, steps, scenario)
        }


class LLMEnhancedGenerator:
    """LLM-enhanced code generation with framework analysis and smart patterns"""
    
    def __init__(self, llm_client=None):
        """Initialize with LLM client for intelligent code generation"""
        self.llm_client = llm_client
        self.reusable_components = None
        self.coding_standards = None
    
    def analyze_framework_repository(self, framework_root: Path) -> Dict[str, Any]:
        """
        Analyze framework repository to detect reusable components
        - Login pages, home pages, base pages
        - Utility functions (Excel, wait helpers, common actions)
        - Coding patterns and standards
        """
        logger.info(f"[LLM Analysis] Analyzing framework at {framework_root}")
        
        if not self.llm_client:
            logger.warning("[LLM Analysis] No LLM client available, skipping analysis")
            return {"reusable_components": [], "coding_standards": [], "utilities": []}
        
        # Scan framework directories
        reusable_files = []
        for pattern in ['**/login*.ts', '**/home*.ts', '**/base*.ts', '**/util*.ts', '**/helper*.ts']:
            for file_path in framework_root.glob(pattern):
                try:
                    content = file_path.read_text(encoding='utf-8')
                    rel_path = file_path.relative_to(framework_root)
                    reusable_files.append({
                        'path': str(rel_path),
                        'content': content[:2000],  # First 2000 chars
                        'type': self._classify_file_type(str(rel_path))
                    })
                except Exception as e:
                    logger.warning(f"[LLM Analysis] Error reading {file_path}: {e}")
        
        if not reusable_files:
            logger.info("[LLM Analysis] No reusable components found")
            return {"reusable_components": [], "coding_standards": [], "utilities": []}
        
        # Ask LLM to analyze reusable components
        analysis_prompt = f"""
Analyze this Playwright test framework repository to identify reusable components and patterns.

Framework files found:
{json.dumps([{'path': f['path'], 'type': f['type']} for f in reusable_files], indent=2)}

Sample content from key files:
{self._format_file_samples(reusable_files[:3])}

Provide a JSON response with:
1. "reusable_components": List of reusable pages/classes with their import paths and usage
   - Example: {{"name": "LoginPage", "import": "../pages/login.page", "methods": ["login", "logout"], "description": "Handles user authentication"}}
2. "coding_standards": List of coding patterns observed
   - Example: {{"pattern": "Page Object Model", "description": "All pages extend BasePage class"}}
3. "utilities": List of utility functions
   - Example: {{"name": "waitForTableLoad", "import": "../utils/wait.helpers", "description": "Waits for dynamic table to load"}}
4. "dynamic_patterns": Common patterns for dynamic elements
   - Example: {{"pattern": "table-row-by-name", "code": "page.locator('table tr').filter({{ hasText: rowName }})"}}  

Return ONLY valid JSON, no markdown or explanations.
"""
        
        try:
            response = self.llm_client.invoke(analysis_prompt)
            response_text = self._extract_content(response)
            # Clean markdown code fences if present
            response_text = response_text.strip()
            if response_text.startswith('```'):
                lines = response_text.split('\n')
                response_text = '\n'.join(lines[1:-1]) if len(lines) > 2 else response_text
                response_text = response_text.replace('```json', '').replace('```', '').strip()
            
            analysis = json.loads(response_text)
            logger.info(f"[LLM Analysis] Found {len(analysis.get('reusable_components', []))} reusable components")
            self.reusable_components = analysis.get('reusable_components', [])
            self.coding_standards = analysis.get('coding_standards', [])
            return analysis
        except Exception as e:
            logger.error(f"[LLM Analysis] Failed to analyze framework: {e}")
            return {"reusable_components": [], "coding_standards": [], "utilities": []}
    
    def _classify_file_type(self, path: str) -> str:
        """Classify file based on path"""
        path_lower = path.lower()
        if 'login' in path_lower:
            return 'authentication'
        elif 'home' in path_lower or 'dashboard' in path_lower:
            return 'navigation'
        elif 'base' in path_lower:
            return 'base_class'
        elif 'util' in path_lower or 'helper' in path_lower:
            return 'utility'
        return 'page'
    
    def _format_file_samples(self, files: List[Dict]) -> str:
        """Format file samples for LLM"""
        samples = []
        for file in files:
            samples.append(f"\n// File: {file['path']} ({file['type']})\n{file['content']}")
        return '\n'.join(samples)
    
    def _extract_content(self, response) -> str:
        """Extract content from LLM response"""
        if hasattr(response, 'content'):
            return response.content
        return str(response)
    
    def generate_enhanced_code(
        self,
        flow_name: str,
        steps: List[Dict[str, Any]],
        start_url: str,
        scenario: str,
        framework_root: Optional[Path] = None,
        framework_analysis: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """
        Generate enhanced code using LLM that:
        1. Leverages reusable components from framework
        2. Follows coding standards
        3. Handles dynamic elements intelligently (tables, dropdowns, loading)
        4. Adds appropriate wait conditions
        """
        logger.info(f"[LLM Enhanced] Generating code for {flow_name}")
        
        if not self.llm_client:
            logger.warning("[LLM Enhanced] No LLM client, falling back to static templates")
            return FrameworkTemplate.generate_all_files(flow_name, steps, start_url, scenario)
        
        # Use provided analysis or perform new one
        if framework_analysis:
            analysis = framework_analysis
        elif framework_root:
            analysis = self.analyze_framework_repository(framework_root)
        else:
            analysis = {"reusable_components": [], "coding_standards": [], "utilities": []}
        
        # Prepare step details for LLM
        step_details = self._prepare_step_details(steps)
        
        # Generate enhanced code with LLM
        enhancement_prompt = self._build_enhancement_prompt(
            flow_name, step_details, start_url, scenario, analysis
        )
        
        try:
            response = self.llm_client.invoke(enhancement_prompt)
            response_text = self._extract_content(response)
            
            # Clean markdown fences
            response_text = response_text.strip()
            if response_text.startswith('```'):
                lines = response_text.split('\n')
                response_text = '\n'.join(lines[1:-1]) if len(lines) > 2 else response_text
                response_text = response_text.replace('```json', '').replace('```', '').strip()
            
            generated_files = json.loads(response_text)
            logger.info(f"[LLM Enhanced] Generated {len(generated_files)} files")
            return generated_files
        except Exception as e:
            logger.error(f"[LLM Enhanced] Failed to generate enhanced code: {e}")
            # Fallback to static templates
            logger.info("[LLM Enhanced] Falling back to static templates")
            return FrameworkTemplate.generate_all_files(flow_name, steps, start_url, scenario)
    
    def _prepare_step_details(self, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prepare step details with enhanced metadata for LLM"""
        enhanced_steps = []
        for idx, step in enumerate(steps, 1):
            # Analyze step for intelligent code generation
            element_type = self._infer_element_type(step)
            is_dynamic = self._is_dynamic_element(step)
            wait_hints = self._infer_wait_requirements(step, idx, steps)
            selection_method = self._infer_selection_method(step)
            
            enhanced_step = {
                'step_number': idx,
                'action': step.get('action', 'click'),
                'navigation': step.get('navigation', ''),
                'locators': step.get('locators', {}),
                'data': step.get('data', ''),
                'expected': step.get('expected', ''),
                'visible_text': step.get('visibleText', ''),  # KEY: What user saw when clicking
                'element_type': element_type,
                'is_dynamic': is_dynamic,
                'wait_requirements': wait_hints,  # When/what to wait for
                'selection_method': selection_method,  # How to select (by-name, by-index, etc.)
                'reasoning': self._generate_step_reasoning(step, element_type, is_dynamic, wait_hints)
            }
            enhanced_steps.append(enhanced_step)
        return enhanced_steps
    
    def _infer_element_type(self, step: Dict[str, Any]) -> str:
        """Infer element type from step data"""
        action = step.get('action', '').lower()
        navigation = step.get('navigation', '').lower()
        visible_text = step.get('visibleText', '').lower()
        
        # Check if dropdown options are captured
        if step.get('dropdownOptions'):
            return 'dropdown'
        
        if action == 'select' or action == 'change' or 'dropdown' in navigation or 'select' in visible_text:
            return 'dropdown'
        elif 'table' in navigation or 'row' in navigation or 'grid' in navigation:
            return 'table'
        elif action in ['fill', 'type', 'input']:
            return 'input'
        elif action == 'click':
            if 'button' in navigation or 'submit' in navigation:
                return 'button'
            elif 'link' in navigation:
                return 'link'
        return 'generic'
    
    def _is_dynamic_element(self, step: Dict[str, Any]) -> bool:
        """Check if element is dynamic (tables, loading indicators, etc.)"""
        navigation = step.get('navigation', '').lower()
        dynamic_keywords = ['table', 'row', 'load', 'wait', 'dynamic', 'search', 'filter', 'result']
        return any(keyword in navigation for keyword in dynamic_keywords)
    
    def _infer_wait_requirements(self, step: Dict[str, Any], step_idx: int, all_steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Infer when and what to wait for based on:
        1. Action type (navigation, search, form submit)
        2. Element type (table, dropdown, dynamic content)
        3. Sequence context (previous step might trigger loading)
        """
        action = step.get('action', '').lower()
        navigation = step.get('navigation', '').lower()
        
        wait_hints = {
            'required': False,
            'type': None,  # 'networkidle', 'element_visible', 'loading_hidden', 'timeout'
            'reason': '',
            'duration_ms': None
        }
        
        # Check previous step for triggers
        if step_idx > 0:
            prev_step = all_steps[step_idx - 1]
            prev_action = prev_step.get('action', '').lower()
            prev_nav = prev_step.get('navigation', '').lower()
            
            # After search/filter, wait for results to load
            if any(kw in prev_nav for kw in ['search', 'filter', 'submit', 'click']):
                wait_hints['required'] = True
                wait_hints['type'] = 'loading_hidden'
                wait_hints['reason'] = f"Previous step '{prev_nav}' likely triggers data loading"
        
        # Navigation actions need networkidle wait
        if action in ['navigate', 'goto'] or 'navigate' in navigation:
            wait_hints['required'] = True
            wait_hints['type'] = 'networkidle'
            wait_hints['reason'] = "Page navigation requires waiting for network to settle"
        
        # Table/search results need loading wait
        if any(kw in navigation for kw in ['table', 'row', 'result', 'grid']):
            wait_hints['required'] = True
            wait_hints['type'] = 'element_visible'
            wait_hints['reason'] = "Dynamic table/results need to be visible before interaction"
        
        # Dropdown/select elements may need to load options
        if self._infer_element_type(step) == 'dropdown':
            wait_hints['required'] = True
            wait_hints['type'] = 'element_visible'
            wait_hints['reason'] = "Dropdown options may load dynamically"
        
        # After form submission, wait for response
        if 'submit' in navigation or 'save' in navigation:
            wait_hints['required'] = True
            wait_hints['type'] = 'networkidle'
            wait_hints['reason'] = "Form submission requires waiting for server response"
        
        # Explicit wait indicators in navigation text
        if 'wait' in navigation or 'loading' in navigation:
            wait_hints['required'] = True
            wait_hints['type'] = 'loading_hidden'
            wait_hints['reason'] = "Explicit loading mentioned in step description"
        
        return wait_hints
    
    def _infer_selection_method(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """
        Determine HOW to select an element, especially for dynamic lists/tables:
        - by-name: Use visible text (from visibleText field)
        - by-index: Use position (less flexible, avoid if possible)
        - by-attribute: Use data attribute or ID
        """
        element_type = self._infer_element_type(step)
        visible_text = step.get('visibleText', '').strip()
        navigation = step.get('navigation', '').lower()
        
        selection = {
            'method': 'direct',  # direct, by-text, by-index, by-filter
            'criteria': None,
            'reason': ''
        }
        
        # Table rows should use visible text if available
        if element_type == 'table' and visible_text:
            selection['method'] = 'by-text'
            selection['criteria'] = visible_text
            selection['reason'] = f"Table row clicked with visible text '{visible_text}' - use flexible text-based selector"
        elif element_type == 'table' and not visible_text:
            selection['method'] = 'by-index'
            selection['criteria'] = 'first'  # Default to first row
            selection['reason'] = "Table row clicked but no visible text captured - consider using index (less flexible)"
        
        # Dropdowns should use label/text from visibleText or data field
        elif element_type == 'dropdown':
            data = step.get('data', '').strip()
            selected_value = step.get('selectedValue', '').strip()
            dropdown_options = step.get('dropdownOptions', [])
            
            if dropdown_options:
                selection['method'] = 'by-text'
                selection['criteria'] = selected_value or visible_text or data
                selection['available_options'] = [opt['text'] for opt in dropdown_options]
                selection['reason'] = f"Dropdown with {len(dropdown_options)} options captured. Selected: '{selected_value or visible_text}'"
            elif visible_text:
                selection['method'] = 'by-text'
                selection['criteria'] = visible_text
                selection['reason'] = f"Dropdown selection by visible label '{visible_text}'"
            elif data:
                selection['method'] = 'by-text'
                selection['criteria'] = data
                selection['reason'] = f"Dropdown selection by data value '{data}'"
        
        # Links/buttons with visible text
        elif visible_text and element_type in ['button', 'link']:
            selection['method'] = 'by-text'
            selection['criteria'] = visible_text
            selection['reason'] = f"Element has visible text '{visible_text}' - use getByText or getByRole"
        
        # Search results or filtered lists
        elif any(kw in navigation for kw in ['search', 'filter', 'find']):
            if visible_text:
                selection['method'] = 'by-filter'
                selection['criteria'] = visible_text
                selection['reason'] = f"Selecting from search/filter results by text '{visible_text}'"
        
        return selection
    
    def _generate_step_reasoning(self, step: Dict[str, Any], element_type: str, 
                                  is_dynamic: bool, wait_hints: Dict[str, Any]) -> str:
        """
        Generate human-readable reasoning for LLM to understand WHY certain patterns are needed
        """
        parts = []
        
        # Element type reasoning
        if element_type == 'table':
            visible_text = step.get('visibleText', '')
            if visible_text:
                parts.append(f"Table interaction detected with visible text '{visible_text}' - generate flexible row selector using filter({{hasText: ...}})")
            else:
                parts.append("Table interaction without captured text - consider by-index selector but note it's brittle")
        elif element_type == 'dropdown':
            parts.append("Dropdown detected - use selectOption with label/text, not value attribute")
        
        # Dynamic element reasoning
        if is_dynamic:
            parts.append("Dynamic element detected - add explicit wait before interaction")
        
        # Wait reasoning
        if wait_hints.get('required'):
            parts.append(f"Wait required: {wait_hints.get('reason', 'Unknown reason')}")
        
        return " | ".join(parts) if parts else "Standard element interaction"
    
    def _build_enhancement_prompt(self, flow_name: str, steps: List[Dict[str, Any]], 
                                  start_url: str, scenario: str, 
                                  analysis: Dict[str, Any]) -> str:
        """
        Build comprehensive prompt for LLM to generate enhanced code matching reference framework
        """
        file_name = FrameworkTemplate.to_snake_case(flow_name)
        class_name = FrameworkTemplate.to_pascal_case(flow_name)
        
        prompt = f"""
You are an expert Playwright test automation engineer. Generate a complete, production-ready test automation suite that EXACTLY matches the reference framework structure.

## Test Scenario
**Flow Name**: {flow_name}
**Scenario**: {scenario}
**Start URL**: {start_url}

## REFERENCE FRAMEWORK STRUCTURE (MUST FOLLOW THIS EXACT FORMAT)

### Locators File Format (locators/<flow-name>.ts):
```typescript
const locators = {{
  elementName: "xpath=//...",
  anotherElement: "xpath=//...",
  buttonName: "xpath=//...",
}};

export default locators;
```
**Rules for Locators:**
- Export a plain object called `locators` (lowercase)
- Use descriptive camelCase keys
- All selectors must be strings (xpath, css, or Playwright)
- Format xpath selectors as "xpath=..." prefix
- Export as default

### Page File Format (pages/<FlowName>Page.ts):
```typescript
import {{ Page, Locator }} from '@playwright/test';
import HelperClass from "../util/methods.utility.ts";
import locators from "../locators/<flow-name>.ts";

class <FlowName>page {{
  page: Page;
  helper: HelperClass;
  elementName: Locator;
  anotherElement: Locator;
  buttonName: Locator;

  constructor(page: Page) {{
    this.page = page;
    this.helper = new HelperClass(page);
    this.elementName = page.locator(locators.elementName);
    this.anotherElement = page.locator(locators.anotherElement);
    this.buttonName = page.locator(locators.buttonName);
  }}
}}

export default <FlowName>page;
```
**Rules for Page:**
- Class name: `<FlowName>page` (lowercase 'page' suffix)
- Must import HelperClass from "../util/methods.utility.ts"
- Must import locators from corresponding locators file
- Initialize ALL locators in constructor using `page.locator(locators.keyName)`
- Export as default
- NO METHODS - Only locator initialization

### Test File Format (tests/<flow-name>.spec.ts):
```typescript
import {{ test }} from "./testSetup.ts";
import PageObject from "../pages/<FlowName>Page.ts";
import {{ getTestToRun, shouldRun, readExcelData }} from "../util/csvFileManipulation.ts";
import {{ attachScreenshot, namedStep }} from "../util/screenshot.ts";
import * as dotenv from 'dotenv';

const path = require('path');
const fs = require('fs');

dotenv.config();
let executionList: any[];

test.beforeAll(() => {{
  executionList = getTestToRun(path.join(__dirname, '../testmanager.xlsx'));
}});

test.describe("{flow_name}", () => {{
  let <flowname>page: PageObject;

  const run = (name: string, fn: ({{ page }}, testinfo: any) => Promise<void>) =>
    (shouldRun(name) ? test : test.skip)(name, fn);

  run("{flow_name}", async ({{ page }}, testinfo) => {{
    <flowname>page = new PageObject(page);
    const testCaseId = testinfo.title;
    const testRow: Record<string, any> = executionList?.find((row: any) => row['TestCaseID'] === testCaseId) ?? {{}};
    
    // Data loading logic (KEEP THIS BOILERPLATE)
    const datasheetFromExcel = String(testRow?.['DatasheetName'] ?? '').trim();
    const dataSheetName = datasheetFromExcel || '';
    const envReferenceId = (process.env.REFERENCE_ID || process.env.DATA_REFERENCE_ID || '').trim();
    const excelReferenceId = String(testRow?.['ReferenceID'] ?? '').trim();
    const dataReferenceId = envReferenceId || excelReferenceId;
    if (dataReferenceId) {{
      console.log(`[ReferenceID] Using: ${{dataReferenceId}} (source: ${{envReferenceId ? 'env' : 'excel'}})`);
    }}
    const dataIdColumn = String(testRow?.['IDName'] ?? '').trim();
    const dataSheetTab = String(testRow?.['SheetName'] ?? testRow?.['Sheet'] ?? '').trim();
    const dataDir = path.join(__dirname, '../data');
    fs.mkdirSync(dataDir, {{ recursive: true }});
    let dataRow: Record<string, any> = {{}};
    
    const ensureDataFile = (): string | null => {{
      if (!dataSheetName) {{
        return null;
      }}
      const expectedPath = path.join(dataDir, dataSheetName);
      if (!fs.existsSync(expectedPath)) {{
        const caseInsensitiveMatch = (() => {{
          try {{
            const entries = fs.readdirSync(dataDir, {{ withFileTypes: false }});
            const target = dataSheetName.toLowerCase();
            const found = entries.find((entry) => entry.toLowerCase() === target);
            return found ? path.join(dataDir, found) : null;
          }} catch (err) {{
            console.warn(`[DATA] Unable to scan data directory for ${{dataSheetName}}:`, err);
            return null;
          }}
        }})();
        if (caseInsensitiveMatch) {{
          return caseInsensitiveMatch;
        }}
        const message = `Test data file '${{dataSheetName}}' not found in data/. Upload the file before running '${{testCaseId}}'.`;
        console.warn(`[DATA] ${{message}}`);
        throw new Error(message);
      }}
      return expectedPath;
    }};
    
    const normaliseKey = (value: string) => value.replace(/[^a-z0-9]/gi, '').toLowerCase();
    const findMatchingDataKey = (sourceKey: string) => {{
      if (!sourceKey || !dataRow) {{
        return undefined;
      }}
      const normalisedSource = normaliseKey(sourceKey);
      return Object.keys(dataRow || {{}}).find((candidate) => normaliseKey(String(candidate)) === normalisedSource);
    }};
    
    const getDataValue = (sourceKey: string, fallback: string) => {{
      if (!sourceKey) {{
        return fallback;
      }}
      const directKey = findMatchingDataKey(sourceKey) || findMatchingDataKey(sourceKey.replace(/([A-Z])/g, '_$1'));
      if (directKey) {{
        const candidate = dataRow?.[directKey];
        if (candidate !== undefined && candidate !== null && `${{candidate}}`.trim() !== '') {{
          return `${{candidate}}`;
        }}
      }}
      return fallback;
    }};
    
    const dataPath = ensureDataFile();
    if (dataPath && dataReferenceId && dataIdColumn) {{
      dataRow = readExcelData(dataPath, dataSheetTab || '', dataReferenceId, dataIdColumn) ?? {{}};
      if (!dataRow || Object.keys(dataRow).length === 0) {{
        console.warn(`[DATA] Row not found in ${{dataSheetName}} for ${{dataIdColumn}}='${{dataReferenceId}}'.`);
      }}
    }} else if (!dataSheetName) {{
      console.log(`[DATA] No DatasheetName configured for ${{testCaseId}}. Test will run with hardcoded/default values.`);
    }} else if (dataSheetName && (!dataReferenceId || !dataIdColumn)) {{
      const missingFields = [];
      if (!dataReferenceId) missingFields.push('ReferenceID');
      if (!dataIdColumn) missingFields.push('IDName');
      const message = `DatasheetName='${{dataSheetName}}' is provided but ${{missingFields.join(' and ')}} ${{missingFields.length > 1 ? 'are' : 'is'}} missing. Please provide ${{missingFields.join(' and ')}} in testmanager.xlsx for '${{testCaseId}}'.`;
      console.error(`[DATA] ${{message}}`);
      throw new Error(message);
    }}

    // TEST STEPS START HERE
    await namedStep("Step 0 - Navigate to application and wait for manual authentication", page, testinfo, async () => {{
      await page.goto("{start_url}");
      // Manual authentication: Complete login steps manually in the browser
      // Wait for first element after authentication
      // await <flowname>page.firstElement.waitFor({{ state: "visible", timeout: 60000 }});
      const screenshot = await page.screenshot();
      attachScreenshot("Step 0 - Navigate to application and wait for manual authentication", testinfo, screenshot);
    }});

    // GENERATE STEPS FROM RECORDED ACTIONS BELOW
    // Each step should use: await namedStep("Step X - Description", page, testinfo, async () => {{ ... }});
    // Access page elements via: <flowname>page.elementName.click()
    // Always capture screenshot: const screenshot = await page.screenshot(); attachScreenshot("Step X", testinfo, screenshot);

  }});
}});
```
**Rules for Test:**
- Import test from "./testSetup.ts" (custom test fixture)
- Import PageObject from pages (use as type)
- MUST include full data loading boilerplate (ensureDataFile, normaliseKey, findMatchingDataKey, getDataValue)
- Use `namedStep` utility for EVERY test step
- Step 0 is ALWAYS navigation + manual auth comment
- Each step: access locators via page object instance, perform action, capture screenshot
- Use `getDataValue()` to fetch test data from Excel when needed
- NO assertions in test - just actions + screenshots


## Recorded Steps
{json.dumps(steps, indent=2)}

## CODE GENERATION INSTRUCTIONS

For EACH recorded step, you must:

### 1. Create a Locator Entry
In locators file, add: `elementName: "xpath=<selector>"`
- Use descriptive names from step action/navigation
- Extract xpath/css from step['locators'] dictionary
- Priority: playwright > css > xpath

### 2. Initialize Locator in Page Constructor
In page constructor, add: `this.elementName = page.locator(locators.elementName);`
- Must match the name in locators file
- Declare as class property: `elementName: Locator;`

### 3. Generate Test Step with namedStep
In test file, for each step create:
```typescript
await namedStep("Step {{idx}} - {{step['navigation']}}", page, testinfo, async () => {{
  // Perform action based on step['action']:
  // - 'click': await <flowname>page.elementName.click();
  // - 'fill'/'type': await <flowname>page.elementName.fill(getDataValue("field_name", "{{step['data']}}"));
  // - 'select': await <flowname>page.elementName.selectOption({{{{ label: "{{step['data']}}" }}}});
  
  // Add wait if needed (check if previous step triggers loading)
  // await page.waitForLoadState('networkidle');
  
  // Capture screenshot (REQUIRED)
  const screenshot = await page.screenshot();
  attachScreenshot("Step {{idx}} - {{step['navigation']}}", testinfo, screenshot);
}});
```

### Action Type Mapping
- **click**: `await page.element.click()`
- **fill/type/input**: `await page.element.fill(value)` - use getDataValue() to fetch from Excel
- **select/change**: `await page.element.selectOption({{{{ label: value }}}})` - use label, not value attr
- **navigate**: `await page.goto(url)`
- **check/uncheck**: `await page.element.check()` or `uncheck()`

### Smart Element Handling
- **Tables**: If navigation mentions "table" or "row", use flexible selector:
  - Locator: `page.getByRole('row').filter({{{{ hasText: step['visibleText'] }}}})` if visibleText available
  - Otherwise: `page.locator('table tr').nth(0)` but note it's brittle
- **Dropdowns**: ALWAYS use label-based selection: `selectOption({{{{ label: "text" }}}})`, NOT value
- **Dynamic elements**: Add `await element.waitFor({{{{ state: "visible" }}}})` before interaction
- **After search/filter**: Add `await page.waitForTimeout(1000)` or wait for loading to disappear

### Data Binding
- For input/select actions, use: `getDataValue("field_name", "default_value")`
- field_name should match a column in Excel (e.g., "Username", "Password", "Country")
- default_value is fallback if Excel not loaded (use recorded data from step['data'])

## Output Format
Return ONLY a valid JSON object with these 3 files (no data file needed):
{{{{
  "locators/{file_name}.ts": "const locators = {{{{ ... }}}}; export default locators;",
  "pages/{class_name}Page.ts": "import ... class {class_name}page {{{{ ... }}}} export default {class_name}page;",
  "tests/{file_name}.spec.ts": "import ... test.describe('{flow_name}', () => {{{{ ... }}}});"
}}}}

**CRITICAL**: 
- NO markdown code fences (```typescript or ```json)
- NO explanatory text before or after JSON
- ONLY the raw JSON object
- File keys must use exact format: "locators/", "pages/", "tests/"
- Must include ALL test boilerplate (data loading, namedStep, screenshots)
"""
        return prompt
