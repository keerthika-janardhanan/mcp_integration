"""
Self-Healing Trial Executor with MCP Integration
Automatically detects and fixes errors during trial runs with up to 5 retry attempts.
"""
import re
import json
from pathlib import Path
from typing import Tuple, Dict, Any, Optional, List
from .executor import run_trial_in_framework
from .core.llm_client_copilot import CopilotClient
import logging

logger = logging.getLogger(__name__)


class SelfHealingTrialExecutor:
    """Executes trial runs with automatic error detection and self-healing."""
    
    MAX_RETRIES = 5
    
    ERROR_PATTERNS = {
        "import_error": r"(Cannot find module|Module not found|is not a constructor|Cannot use import statement)",
        "export_error": r"(is not a constructor|has no exported member|does not provide an export)",
        "locator_error": r"(locator.*not found|element.*not found|selector.*not found|Timeout.*exceeded|locator\.waitFor.*Timeout|waiting for locator)",
        "strict_mode_violation": r"(strict mode violation.*resolved to \d+ elements)",
        "data_file_error": r"(Data file not found|ENOENT.*\.xlsx)",
        "type_error": r"(TypeError:|Type '.*' is not assignable to type)",
        "syntax_error": r"(SyntaxError:|Unexpected token)",
        "missing_method": r"(is not a function|Cannot read property.*of undefined)",
        "compilation_error": r"(TSError:|TS\d+:)",
    }
    
    def __init__(self, llm_client: Optional[CopilotClient] = None, recorder_metadata: Optional[Dict[str, Any]] = None):
        """Initialize with optional LLM client and recorder metadata for fixes."""
        self.llm = llm_client or CopilotClient(temperature=0.1)
        self.fix_history: List[Dict[str, Any]] = []
        self.files_fixed_this_run: List[str] = []  # Track which files were fixed
        self.recorder_metadata = recorder_metadata or {}  # Store recorder data for locator fixes
        self.tried_locators: Dict[str, List[str]] = {}  # Track which locators we've tried for each failing selector
    
    def execute_with_retry(
        self,
        script_content: str,
        framework_root: Path,
        headed: bool = True,
        env_overrides: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Execute trial with automatic error detection and self-healing.
        
        Returns:
            Dict with keys: success, logs, attempts, fixes_applied, final_content
        """
        logger.info("[Self-Healing] ========== STARTING SELF-HEALING EXECUTION ==========")
        logger.info(f"[Self-Healing] Framework root: {framework_root}")
        logger.info(f"[Self-Healing] Recorder metadata available: {self.recorder_metadata is not None}")
        if self.recorder_metadata:
            actions_count = len(self.recorder_metadata.get('actions', []))
            logger.info(f"[Self-Healing] Recorder has {actions_count} actions")
        
        current_content = script_content
        attempt = 0
        all_logs = []
        fixes_applied = []
        self.files_fixed_this_run = []  # Reset for this execution
        
        try:
            while attempt < self.MAX_RETRIES:
                attempt += 1
                logger.info(f"[Self-Healing] ========== ATTEMPT {attempt}/{self.MAX_RETRIES} ==========")
                
                # Run trial
                try:
                    success, logs = run_trial_in_framework(
                        current_content,
                        framework_root,
                        headed=headed,
                        env_overrides=env_overrides
                    )
                except Exception as e:
                    logger.error(f"[Self-Healing] Exception during trial execution: {e}", exc_info=True)
                    logs = f"Trial execution exception: {e}"
                    success = False
                
                all_logs.append(f"\n{'='*80}\nATTEMPT {attempt}\n{'='*80}\n{logs}")
                
                if success:
                    logger.info(f"[Self-Healing] ✓ Success on attempt {attempt}")
                    return {
                        "success": True,
                        "logs": "\n".join(all_logs),
                        "attempts": attempt,
                        "fixes_applied": fixes_applied,
                        "final_content": current_content,
                    }
                
                logger.info(f"[Self-Healing] ✗ Attempt {attempt} failed, analyzing error...")
                
                # Detect error type
                error_type, error_details = self._detect_error(logs)
                
                if not error_type:
                    logger.warning(f"[Self-Healing] Unknown error type, cannot auto-fix")
                    logger.warning(f"[Self-Healing] Logs sample: {logs[:1000]}")
                    break
                
                logger.info(f"[Self-Healing] Detected error type: {error_type}")
                logger.info(f"[Self-Healing] Error match: {error_details.get('match', 'N/A')[:200]}")
                
                # Track if any fix was applied (content OR files)
                pre_fix_files_count = len(self.files_fixed_this_run)
                
                # Attempt fix
                try:
                    fixed_content = self._apply_fix(
                        current_content,
                        error_type,
                        error_details,
                        logs,
                        framework_root
                    )
                except Exception as e:
                    logger.error(f"[Self-Healing] Exception during fix application: {e}", exc_info=True)
                    break
                
                # Check if any fix was applied
                content_changed = (fixed_content != current_content)
                files_fixed = (len(self.files_fixed_this_run) > pre_fix_files_count)
                
                logger.info(f"[Self-Healing] Fix results: content_changed={content_changed}, files_fixed={files_fixed}")
                
                if not content_changed and not files_fixed:
                    logger.warning(f"[Self-Healing] No fix generated (content unchanged, no files fixed), stopping retries")
                    break
                
                # Build fix description
                if files_fixed:
                    new_files = self.files_fixed_this_run[pre_fix_files_count:]
                    fix_description = f"Fixed {len(new_files)} page file(s): {', '.join(new_files)}"
                else:
                    fix_description = self._describe_fix(current_content, fixed_content)
                
                fixes_applied.append({
                    "attempt": attempt,
                    "error_type": error_type,
                    "error_details": error_details,
                    "fix_description": fix_description,
                    "files_fixed": files_fixed,
                    "content_changed": content_changed,
                })
                
                logger.info(f"[Self-Healing] Applied fix: {fix_description}")
                current_content = fixed_content
        
        except Exception as e:
            logger.error(f"[Self-Healing] Fatal exception in retry loop: {e}", exc_info=True)
            all_logs.append(f"\n[Self-Healing] Fatal error: {e}")
        
        # All retries exhausted
        logger.info(f"[Self-Healing] ========== SELF-HEALING COMPLETE: FAILED ==========")
        return {
            "success": False,
            "logs": "\n".join(all_logs),
            "attempts": attempt,
            "fixes_applied": fixes_applied,
            "final_content": current_content,
            "error": "Max retries exceeded without successful execution",
        }
    
    def _detect_error(self, logs: str) -> Tuple[Optional[str], Dict[str, Any]]:
        """Detect error type from logs using regex patterns."""
        logger.info(f"[Self-Healing] Detecting error in logs (length: {len(logs)})")
        
        for error_type, pattern in self.ERROR_PATTERNS.items():
            match = re.search(pattern, logs, re.IGNORECASE)
            if match:
                logger.info(f"[Self-Healing] Matched error pattern: {error_type}")
                # Extract context around error
                lines = logs.split("\n")
                error_line_idx = next(
                    (i for i, line in enumerate(lines) if match.group(0) in line),
                    None
                )
                
                context = []
                if error_line_idx is not None:
                    start = max(0, error_line_idx - 3)
                    end = min(len(lines), error_line_idx + 4)
                    context = lines[start:end]
                
                # Extract file and line number if present
                file_match = re.search(r"at\s+(.*):(\d+):(\d+)", logs)
                
                return error_type, {
                    "match": match.group(0),
                    "context": "\n".join(context),
                    "file": file_match.group(1) if file_match else None,
                    "line": file_match.group(2) if file_match else None,
                }
        
        logger.warning(f"[Self-Healing] No error pattern matched in logs")
        logger.debug(f"[Self-Healing] First 500 chars of logs: {logs[:500]}")
        return None, {}
    
    def _apply_fix(
        self,
        content: str,
        error_type: str,
        error_details: Dict[str, Any],
        full_logs: str,
        framework_root: Path,
    ) -> str:
        """Apply appropriate fix based on error type."""
        
        logger.info(f"[Self-Healing] Applying fix for error_type={error_type}")
        
        # Quick fixes that don't need LLM
        if error_type == "export_error":
            logger.info(f"[Self-Healing] Attempting to fix export error in imported files")
            # First try to fix imported page files
            content, files_fixed = self._fix_export_error_in_imported_files(
                content, error_details, framework_root
            )
            if files_fixed:
                logger.info("[Self-Healing] Fixed export in imported page file(s)")
                return content  # Return same content, but files are fixed
            
            logger.info("[Self-Healing] No files fixed, trying to fix test content itself")
            # Fallback: fix in test content itself (less common)
            return self._fix_export_error(content, error_details)
        
        if error_type == "import_error":
            return self._fix_import_error(content, error_details, framework_root)
        
        # Syntax errors caused by invalid locators (getByTestId in locator strings)
        if error_type == "syntax_error" and ("getByTestId" in full_logs or "getByRole" in full_logs or "getByLabel" in full_logs):
            logger.info("[Self-Healing] Syntax error caused by Playwright method in locator string - treating as locator error")
            return self._fix_locator_error(content, error_details, full_logs, framework_root)
        
        if error_type == "locator_error" or error_type == "strict_mode_violation":
            return self._fix_locator_error(content, error_details, full_logs, framework_root)
        
        # Data file errors cannot be auto-fixed - skip
        if error_type == "data_file_error":
            logger.warning("[Self-Healing] Data file error cannot be auto-fixed")
            return content
        
        # Complex fixes that need LLM
        return self._llm_fix(content, error_type, error_details, full_logs)
    
    def _fix_export_error(self, content: str, error_details: Dict[str, Any]) -> str:
        """Fix missing export statements in page classes."""
        # Pattern: class ClassName { ... } without export default
        pattern = r"(class\s+(\w+Page)\s*\{[^}]*\})\s*(?!export\s+default)"
        
        def add_export(match):
            class_declaration = match.group(1)
            class_name = match.group(2)
            return f"{class_declaration}\n\nexport default {class_name};"
        
        fixed = re.sub(pattern, add_export, content, flags=re.DOTALL)
        
        # Also check for files that end without export default
        if "class " in fixed and not fixed.strip().endswith(";"):
            # Find last class name
            class_matches = list(re.finditer(r"class\s+(\w+Page)", fixed))
            if class_matches:
                last_class_name = class_matches[-1].group(1)
                if f"export default {last_class_name}" not in fixed:
                    fixed = fixed.rstrip() + f"\n\nexport default {last_class_name};\n"
        
        return fixed
    
    def _fix_export_error_in_imported_files(
        self,
        test_content: str,
        error_details: Dict[str, Any],
        framework_root: Path,
    ) -> Tuple[str, bool]:
        """Fix export errors in imported page files.
        
        Returns:
            (test_content, files_fixed) - test content unchanged, but page files are fixed
        """
        error_msg = error_details.get("match", "")
        logger.info(f"[Self-Healing] Analyzing error message: {error_msg}")
        
        # Extract the problematic import from error message
        # Example: "_WorkdayCollaborativePt10SignInToWorkdayPages.default is not a constructor"
        import_match = re.search(r"_(\w+)Pages?\.default is not a constructor", error_msg)
        if not import_match:
            import_match = re.search(r"_(\w+)\.default is not a constructor", error_msg)
        
        if not import_match:
            logger.warning(f"[Self-Healing] Could not extract class name from error: {error_msg}")
            return test_content, False
        
        class_base = import_match.group(1)
        logger.info(f"[Self-Healing] Detected missing export in class: {class_base}")
        
        # Find the import statement in test content to get file path
        import_pattern = rf"import\s+\w+\s+from\s+['\"]([^'\"]+{class_base}[^'\"]*\.(?:pages?\.)?ts)['\"]"
        import_statement = re.search(import_pattern, test_content, re.IGNORECASE)
        
        if not import_statement:
            logger.warning(f"[Self-Healing] Could not find import statement for {class_base}")
            return test_content, False
        
        relative_path = import_statement.group(1)
        logger.info(f"[Self-Healing] Found import path: {relative_path}")
        
        # Resolve relative path from tests directory
        tests_dir = framework_root / "tests"
        if relative_path.startswith("../"):
            target_file = (tests_dir / relative_path).resolve()
        else:
            target_file = (framework_root / relative_path).resolve()
        
        if not target_file.exists():
            logger.warning(f"[Self-Healing] Page file not found: {target_file}")
            return test_content, False
        
        logger.info(f"[Self-Healing] Fixing page file: {target_file}")
        
        try:
            # Read page file
            page_content = target_file.read_text(encoding="utf-8")
            
            # Fix export
            fixed_content = self._fix_export_error(page_content, error_details)
            
            if fixed_content == page_content:
                logger.warning(f"[Self-Healing] No changes made to {target_file}")
                return test_content, False
            
            # Write fixed content
            target_file.write_text(fixed_content, encoding="utf-8")
            logger.info(f"[Self-Healing] ✓ Fixed export in {target_file.name}")
            
            # Track this file as fixed
            self.files_fixed_this_run.append(target_file.name)
            
            return test_content, True
            
        except Exception as e:
            logger.error(f"[Self-Healing] Failed to fix {target_file}: {e}")
            return test_content, False
    
    def _fix_import_error(
        self,
        content: str,
        error_details: Dict[str, Any],
        framework_root: Path,
    ) -> str:
        """Fix import path issues."""
        error_msg = error_details.get("match", "")
        
        # Check if it's a missing .ts extension
        if "Cannot find module" in error_msg:
            # Add .ts to imports without extensions
            pattern = r"from\s+['\"]([^'\"]+)['\"]"
            
            def fix_import(match):
                import_path = match.group(1)
                # Skip node_modules imports
                if not import_path.startswith('.') and not import_path.startswith('/'):
                    return match.group(0)
                # Skip if already has extension
                if import_path.endswith(('.ts', '.js', '.tsx', '.jsx')):
                    return match.group(0)
                # Add .ts extension
                return f"from '{import_path}.ts'"
            
            content = re.sub(pattern, fix_import, content)
        
        # Fix relative path depth issues
        if "Module not found" in error_msg:
            # This requires checking actual file structure
            pass  # Let LLM handle complex path fixes
        
        return content
    
    def _fix_locator_error(
        self,
        content: str,
        error_details: Dict[str, Any],
        full_logs: str,
        framework_root: Path,
    ) -> str:
        """Fix locator timeout/not found errors using recorder metadata."""
        logger.info("[Self-Healing] Attempting locator fix using recorder metadata")
        
        error_msg = error_details.get("match", "")
        
        # Extract failing locator from error message or logs
        # Use greedy patterns that match until the closing delimiter
        patterns = [
            r"waiting for locator\('(.+?)'\) to",  # waiting for locator('...') to be visible
            r"waiting for locator\(\"(.+?)\"\) to",  # waiting for locator("...") to be visible
            r"locator\('(.+?)'\)\.waitFor",  # locator('...').waitFor
            r'locator\("(.+?)"\)\.waitFor',  # locator("...").waitFor
            r"locator\('(.+?)'\)",  # locator('selector')
            r'locator\("(.+?)"\)',  # locator("selector")
            r"selector:\s*'(.+?)'",  # selector: 'selector'
            r'selector:\s*"(.+?)"',  # selector: "selector"
            r"strict mode violation: locator\('(.+?)'\) resolved",  # strict mode violation
            r'strict mode violation: locator\("(.+?)"\) resolved',  # strict mode violation
        ]
        
        failing_locator = None
        search_text = error_msg + "\n" + full_logs
        for pattern in patterns:
            match = re.search(pattern, search_text, re.DOTALL)
            if match:
                failing_locator = match.group(1)
                logger.info(f"[Self-Healing] Matched pattern: {pattern}")
                break
        
        if not failing_locator:
            logger.warning("[Self-Healing] Could not extract failing locator from error")
            logger.warning(f"[Self-Healing] Error message: {error_msg[:200]}")
            # Don't fall back to LLM for locator errors - return unchanged
            return content
        
        logger.info(f"[Self-Healing] Extracted failing locator: {failing_locator}")
        
        # For strict mode violations, extract suggested locators from error message
        suggested_locators = []
        if "strict mode violation" in error_msg.lower():
            # Extract getByTestId suggestions: "aka getByTestId('login-button')"
            testid_matches = re.findall(r"getByTestId\('([^']+)'\)", search_text)
            for testid in testid_matches:
                suggested_locators.append(f"getByTestId('{testid}')")
                logger.info(f"[Self-Healing] Found suggested locator from error: getByTestId('{testid}')")
        
        # Get alternative locators from recorder metadata
        alternatives = self._get_alternative_locators(failing_locator)
        
        if not alternatives:
            logger.warning(f"[Self-Healing] No alternatives found for locator: {failing_locator}")
            if self.recorder_metadata:
                actions_count = len(self.recorder_metadata.get('actions', []))
                logger.warning(f"[Self-Healing] Recorder has {actions_count} actions but none match this locator")
            # Don't fall back to LLM - return unchanged
            return content
        
        logger.info(f"[Self-Healing] Found {len(alternatives)} alternative(s)")
        
        # Generate locator variations (simplified, combinations, etc.)
        all_locator_options = self._generate_locator_variations(
            failing_locator, alternatives, suggested_locators
        )
        
        # Track which locators we've tried for this selector
        if failing_locator not in self.tried_locators:
            self.tried_locators[failing_locator] = []
        
        # Pick the next untried locator
        fixed_locator = None
        for option in all_locator_options:
            if option not in self.tried_locators[failing_locator]:
                fixed_locator = option
                self.tried_locators[failing_locator].append(option)
                break
        
        if not fixed_locator:
            logger.warning(f"[Self-Healing] All {len(all_locator_options)} locator variations already tried")
            return content
        
        logger.info(f"[Self-Healing] Trying locator variation {len(self.tried_locators[failing_locator])}/{len(all_locator_options)}: {fixed_locator}")
        
        # Replace locator in page files (not test file)
        success = self._replace_locator_in_pages(
            failing_locator, fixed_locator, framework_root
        )
        
        if success:
            logger.info(f"[Self-Healing] ✓ Replaced locator in page files: {failing_locator} -> {fixed_locator}")
        else:
            logger.warning("[Self-Healing] ✗ Could not replace locator in page files")
        
        return content  # Content stays same, but page files are fixed
    
    def _get_alternative_locators(self, failing_locator: str) -> List[Dict[str, Any]]:
        """Extract alternative selectors from recorder metadata."""
        alternatives = []
        
        if not self.recorder_metadata:
            logger.warning("[Self-Healing] No recorder metadata available")
            return alternatives
        
        # Search through recorder actions for matching selectors
        actions = self.recorder_metadata.get("actions", [])
        logger.info(f"[Self-Healing] Searching through {len(actions)} recorder actions")
        
        # Normalize the failing locator for comparison
        failing_normalized = failing_locator.replace('"', "'").replace(" ", "").lower()
        
        # Extract key attributes from failing locator for semantic matching
        # e.g., button[type='submit'][data-automation-id='signInButton']
        # Extract: element type (button), attributes (submit, signInButton, signIn, etc.)
        import re as _re
        element_type_match = _re.match(r'^([a-z]+)', failing_locator.lower())
        element_type = element_type_match.group(1) if element_type_match else None
        
        # Extract semantic keywords (signIn, submit, login, etc.)
        semantic_keywords = _re.findall(r'[a-z]{4,}', failing_locator.lower())
        logger.info(f"[Self-Healing] Semantic keywords from failing locator: {semantic_keywords}")
        
        for idx, action in enumerate(actions):
            element = action.get("element", {})
            selector = element.get("selector", {})
            html = element.get("html", "")
            
            # Extract selectors
            css = selector.get("css", "")
            xpath = selector.get("xpath", "")
            playwright = selector.get("playwright", {})
            visible_text = action.get("visibleText", "")
            action_type = action.get("action", "")
            
            # Normalize for comparison
            css_normalized = css.replace('"', "'").replace(" ", "").lower() if css else ""
            xpath_normalized = xpath.replace('"', "'").replace(" ", "").lower() if xpath else ""
            html_lower = html.lower()
            
            # Check if this action matches the failing locator
            is_match = False
            match_reason = ""
            
            # 1. Exact or substring match
            if css and (css_normalized == failing_normalized or failing_normalized in css_normalized or css_normalized in failing_normalized):
                is_match = True
                match_reason = "exact CSS match"
            elif xpath and (xpath_normalized == failing_normalized or failing_normalized in xpath_normalized):
                is_match = True
                match_reason = "exact XPath match"
            
            # 2. Semantic match: same element type + shared keywords
            elif element_type and semantic_keywords:
                # Check if element type matches (button, input, etc.)
                html_has_element = f'<{element_type}' in html_lower or css.lower().startswith(element_type)
                
                if html_has_element:
                    # Check how many semantic keywords match
                    matches = sum(1 for keyword in semantic_keywords if keyword in html_lower or keyword in css_normalized or keyword in str(playwright).lower())
                    
                    if matches >= 1:  # At least one keyword matches
                        is_match = True
                        match_reason = f"semantic match ({matches} keywords: {[k for k in semantic_keywords if k in html_lower or k in css_normalized]})"
            
            if is_match:
                logger.info(f"[Self-Healing] Match found in action {idx+1} ({action_type}): {match_reason}")
                alt = {
                    "css": css,
                    "xpath": xpath,
                    "visible_text": visible_text,
                    "playwright": playwright,
                    "action_type": action_type,
                    "timestamp": action.get("timestamp", ""),
                    "page_url": action.get("pageUrl", ""),
                    "match_reason": match_reason,
                }
                
                # Only add if it has at least one non-empty selector
                if any([css, xpath, playwright, visible_text]):
                    alternatives.append(alt)
                    logger.info(f"[Self-Healing]   - CSS: {css[:80]}...")
                    if playwright:
                        logger.info(f"[Self-Healing]   - Playwright: {playwright}")
        
        logger.info(f"[Self-Healing] Found {len(alternatives)} alternative selector(s)")
        return alternatives
    
    def _generate_locator_variations(
        self,
        failing_locator: str,
        alternatives: List[Dict[str, Any]],
        suggested_locators: List[str] = None
    ) -> List[str]:
        """
        Generate multiple locator variations to try progressively.
        
        Strategy:
        0. Suggested locators from error message (for strict mode violations - HIGHEST priority)
        1. Simplified versions of failing locator (remove attributes one by one)
        2. Playwright methods from recorder (getByRole, getByTestId, etc.)
        3. CSS selectors from recorder
        4. XPath from recorder
        5. Text-based selectors
        
        Returns: List of locators to try in order
        """
        variations = []
        
        # 0. Add suggested locators from error message (strict mode violations)
        # BUT: Convert getByTestId to CSS selector since framework uses page.locator()
        if suggested_locators:
            logger.info(f"[Self-Healing] Processing {len(suggested_locators)} suggested locators from error")
            for suggestion in suggested_locators:
                # Convert Playwright methods to CSS selectors
                if suggestion.startswith('getByTestId('):
                    # Extract testid: getByTestId('login-button') -> [data-testid="login-button"]
                    testid_match = re.match(r"getByTestId\('([^']+)'\)", suggestion)
                    if testid_match:
                        testid = testid_match.group(1)
                        css_selector = f"[data-testid='{testid}']"
                        variations.insert(0, css_selector)
                        logger.info(f"[Self-Healing] Converted {suggestion} → {css_selector}")
                elif suggestion.startswith('getByRole('):
                    # Skip - harder to convert, will use recorder alternatives instead
                    logger.info(f"[Self-Healing] Skipping {suggestion} (use CSS from recorder)")
                    continue
                else:
                    variations.append(suggestion)
        
        # 1. Generate simplified CSS variations from failing locator
        # Example: button[type='submit'][data-automation-id='signInButton']
        #   -> button[type='submit']
        #   -> button[data-automation-id='signInButton']
        #   -> button
        if '[' in failing_locator:
            import re as _re
            # Extract base element
            base_match = _re.match(r'^([a-z]+)', failing_locator.lower())
            if base_match:
                base_element = base_match.group(1)
                
                # Extract all attributes
                attr_pattern = r'\[([^\]]+)\]'
                attrs = _re.findall(attr_pattern, failing_locator)
                
                # Try with each single attribute
                for attr in attrs:
                    variations.append(f"{base_element}[{attr}]")
                
                # Try base element only
                variations.append(base_element)
        
        # 2. Add Playwright methods from recorder (convert to CSS)
        for alt in alternatives:
            playwright = alt.get('playwright', {})
            if playwright:
                # getByTestId - convert to CSS
                if playwright.get('method') == 'getByTestId':
                    test_id = playwright.get('testId', '')
                    if test_id:
                        css_selector = f"[data-testid='{test_id}']"
                        variations.insert(0, css_selector)
                        logger.info(f"[Self-Healing] Converted getByTestId → {css_selector}")
                
                # getByRole - skip (hard to convert to CSS reliably)
                # getByLabel - skip (hard to convert to CSS reliably)  
                # getByText - skip (hard to convert to CSS reliably)
        
        # 3. Add CSS selectors from recorder
        for alt in alternatives:
            css = alt.get('css', '')
            if css and css not in variations:
                variations.append(css)
        
        # 4. Add text-based selectors if visible text available
        for alt in alternatives:
            visible_text = alt.get('visible_text', '')
            if visible_text and len(visible_text) < 50:
                text_selector = f"text='{visible_text}'"
                if text_selector not in variations:
                    variations.append(text_selector)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_variations = []
        for var in variations:
            if var and var not in seen:
                seen.add(var)
                unique_variations.append(var)
        
        logger.info(f"[Self-Healing] Generated {len(unique_variations)} locator variations:")
        for i, var in enumerate(unique_variations[:10], 1):  # Log first 10
            logger.info(f"[Self-Healing]   {i}. {var[:100]}")
        
        return unique_variations
    
    def _ask_llm_for_best_locator(
        self,
        failing_locator: str,
        alternatives: List[Dict[str, Any]],
        error_msg: str,
        full_logs: str,
    ) -> Optional[str]:
        """Use LLM to select the best alternative locator."""
        
        # Format alternatives for prompt
        alts_text = "\n".join([
            f"Option {i+1}:\n  CSS: {alt.get('css', 'N/A')}\n  XPath: {alt.get('xpath', 'N/A')}\n  Visible Text: {alt.get('visible_text', 'N/A')}\n  Playwright: {alt.get('playwright', {})}"
            for i, alt in enumerate(alternatives)
        ])
        
        prompt = f"""A Playwright test failed because this locator timed out:
FAILING LOCATOR: {failing_locator}

ERROR: {error_msg}

From the recorder metadata, here are alternative selectors that were captured for the same element:
{alts_text}

Your task:
1. Analyze which alternative selector is most reliable for Playwright
2. Prefer Playwright's getByTestId/getByRole/getByLabel/getByText methods over CSS/XPath
3. If playwright methods available, use those (e.g., 'getByTestId("username")')
4. If no playwright methods, prefer CSS selectors over XPath
5. Choose one that's most likely to be stable and visible

Return ONLY the selector string in the correct format for Playwright page.locator():
- For CSS: return the CSS selector as-is (e.g., "#input-t7rh2" or "button[type='submit']")
- For playwright methods: return the method call (e.g., "getByTestId('username')")
- For XPath: return the XPath as-is (e.g., "//input[@id='username']")

Return the best selector string (JUST the string, no explanation or code blocks):"""
        
        try:
            response = self.llm.invoke(prompt)
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            # Extract just the selector (remove any markdown formatting)
            selector = response_text.strip()
            selector = re.sub(r'^```.*?\n|```$', '', selector, flags=re.MULTILINE)
            selector = selector.strip()
            
            logger.info(f"[Self-Healing] LLM suggested locator: {selector}")
            return selector
            
        except Exception as e:
            logger.error(f"[Self-Healing] LLM locator selection failed: {e}")
            return None
    
    def _replace_locator_in_pages(
        self,
        old_locator: str,
        new_locator: str,
        framework_root: Path,
    ) -> bool:
        """Replace locator in page object and locator files."""
        logger.info(f"[Self-Healing] Looking for locator to replace:")
        logger.info(f"[Self-Healing]   OLD: {old_locator}")
        logger.info(f"[Self-Healing]   NEW: {new_locator}")
        
        success = False
        
        # Find all page and locator files
        pages_dir = framework_root / "pages"
        locators_dir = framework_root / "locators"
        
        for directory in [pages_dir, locators_dir]:
            if not directory.exists():
                logger.info(f"[Self-Healing] Directory does not exist: {directory}")
                continue
            
            logger.info(f"[Self-Healing] Scanning directory: {directory}")
            file_count = 0
            for file_path in directory.rglob("*.ts"):
                file_count += 1
                try:
                    content = file_path.read_text(encoding='utf-8')
                    
                    # Create variations of old_locator to match escaped versions
                    # The error shows: button[type=\'submit\'][data-automation-id=\'signInButton\']
                    # But in file it might be: button[type='submit'][data-automation-id='signInButton']
                    old_variations = [
                        old_locator,  # Original
                        old_locator.replace("'", "\\'"),  # Escaped single quotes
                        old_locator.replace('"', '\\"'),  # Escaped double quotes
                        old_locator.replace("\\'", "'"),  # Unescape if already escaped
                        old_locator.replace('\\"', '"'),  # Unescape if already escaped
                    ]
                    
                    # Replace locator strings with various quote styles
                    modified = False
                    for old_var in old_variations:
                        patterns = [
                            (f'"{old_var}"', f'"{new_locator}"'),
                            (f"'{old_var}'", f"'{new_locator}'"),
                            (f'`{old_var}`', f'`{new_locator}`'),
                        ]
                        
                        for old_pattern, new_pattern in patterns:
                            if old_pattern in content:
                                content = content.replace(old_pattern, new_pattern)
                                modified = True
                                logger.info(f"[Self-Healing] ✓ Found and replaced pattern: {old_pattern[:80]}...")
                    
                    if modified:
                        file_path.write_text(content, encoding='utf-8')
                        logger.info(f"[Self-Healing] ✓ Updated locator in: {file_path.name}")
                        self.files_fixed_this_run.append(str(file_path.name))
                        success = True
                        
                except Exception as e:
                    logger.error(f"[Self-Healing] Error updating {file_path}: {e}")
            
            logger.info(f"[Self-Healing] Scanned {file_count} TypeScript files in {directory.name}")
        
        if not success:
            logger.warning(f"[Self-Healing] ✗ Locator not found in any page/locator files")
        
        return success
    
    def _llm_fix(
        self,
        content: str,
        error_type: str,
        error_details: Dict[str, Any],
        full_logs: str,
    ) -> str:
        """Use LLM to generate fix for complex errors."""
        prompt = self._build_fix_prompt(content, error_type, error_details, full_logs)
        
        try:
            response = self.llm.invoke(prompt)
            
            # Try to extract code from response (handle CopilotResponse object)
            response_text = response.content if hasattr(response, 'content') else str(response)
            fixed_content = self._extract_fixed_code(response_text, content)
            return fixed_content
            
        except Exception as e:
            logger.error(f"[Self-Healing] LLM fix failed: {e}")
            return content
    
    def _build_fix_prompt(
        self,
        content: str,
        error_type: str,
        error_details: Dict[str, Any],
        full_logs: str,
    ) -> str:
        """Build prompt for LLM to fix the error."""
        error_context = error_details.get("context", "")
        error_msg = error_details.get("match", "")
        
        return f"""Fix the following TypeScript Playwright test error:

ERROR TYPE: {error_type}
ERROR MESSAGE: {error_msg}

ERROR CONTEXT FROM LOGS:
```
{error_context}
```

CURRENT CODE:
```typescript
{content[:2000]}  // Truncated for brevity
```

FULL ERROR LOGS:
```
{full_logs[-1000:]}  // Last 1000 chars
```

INSTRUCTIONS:
1. Identify the root cause of the error
2. Provide the COMPLETE fixed TypeScript code
3. Ensure all imports have correct paths and extensions
4. Ensure all classes are properly exported with "export default ClassName;"
5. Fix any syntax or type errors
6. If reading Excel data, use: const xlsx=require('xlsx'); workBook=xlsx.readFile(path); allData=xlsx.utils.sheet_to_json(workSheet);
7. Data files must be in ../data/ folder (NOT ../testdata/)
8. After reading data, validate: if (!dataRow || Object.keys(dataRow).length === 0) throw new Error('No test data found');

Return ONLY the fixed TypeScript code, no explanations."""
    
    def _extract_fixed_code(self, llm_response: str, original: str) -> str:
        """Extract fixed code from LLM response."""
        # Try to extract from code blocks
        code_block_pattern = r"```(?:typescript|ts)?\s*([\s\S]*?)\s*```"
        matches = re.findall(code_block_pattern, llm_response)
        
        if matches:
            # Use the largest code block
            return max(matches, key=len).strip()
        
        # If no code blocks, check if response looks like code
        if "import {" in llm_response or "class " in llm_response:
            return llm_response.strip()
        
        # No valid code found
        return original
    
    def _describe_fix(self, original: str, fixed: str) -> str:
        """Generate a human-readable description of what was fixed."""
        if original == fixed:
            return "No changes"
        
        # Count differences
        orig_lines = original.split("\n")
        fixed_lines = fixed.split("\n")
        
        added = len(fixed_lines) - len(orig_lines)
        
        # Check for specific fixes
        fixes = []
        
        if "export default" in fixed and "export default" not in original:
            fixes.append("Added export default statements")
        
        if fixed.count(".ts'") > original.count(".ts'"):
            fixes.append("Added .ts extensions to imports")
        
        if not fixes:
            fixes.append(f"Modified code ({added:+d} lines)")
        
        return ", ".join(fixes)


def execute_trial_with_self_healing(
    script_content: str,
    framework_root: Path,
    headed: bool = True,
    env_overrides: Optional[Dict[str, str]] = None,
    recorder_metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Convenience function to execute trial with self-healing.
    
    Args:
        script_content: The test script content
        framework_root: Path to framework repository root
        headed: Whether to run browser in headed mode
        env_overrides: Environment variable overrides
        recorder_metadata: Optional recorder JSON metadata for locator fixing
    
    Usage:
        result = execute_trial_with_self_healing(code, Path("/repo"), headed=False, recorder_metadata=rec_data)
        if result["success"]:
            print(f"✓ Success after {result['attempts']} attempts")
            print(f"Fixes applied: {result['fixes_applied']}")
        else:
            print(f"✗ Failed after {result['attempts']} attempts")
    """
    executor = SelfHealingTrialExecutor(recorder_metadata=recorder_metadata)
    return executor.execute_with_retry(
        script_content,
        framework_root,
        headed=headed,
        env_overrides=env_overrides,
    )
