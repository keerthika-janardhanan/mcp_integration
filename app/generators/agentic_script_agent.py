"""Agentic workflow for generating Playwright test scripts aligned with framework standards."""

from __future__ import annotations

import json
import os
import re
import posixpath
from collections import Counter
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Set
import ast

# Defensive optional imports: keyword-inspect and other non-LLM endpoints should not 500
# just because langchain or langchain-openai isn't installed in a minimal environment.
try:  # pragma: no cover - import guards
    from langchain.prompts import PromptTemplate  # type: ignore
except ImportError:  # Lightweight fallback with compatible .format()
    class PromptTemplate:  # type: ignore
        def __init__(self, input_variables, template: str):
            self.input_variables = input_variables
            self.template = template

        def format(self, **kwargs) -> str:
            return self.template.format(**kwargs)

try:  # pragma: no cover - import guards
    from langchain_openai import AzureChatOpenAI  # type: ignore
except ImportError:
    AzureChatOpenAI = None  # type: ignore

"""Agent responsible for generating previews and deterministic script payloads.

Key reliability adjustments (Oct/Nov 2025):
 - Use package-relative imports so FastAPI app import context doesn't break.
 - Gracefully degrade when Azure OpenAI env vars are missing instead of raising 500.
 - Wrap LLM invocations; return explicit sentinel messages when unavailable.
"""

# from .orchestrator import TestScriptOrchestrator  # Removed - unused file
from ..core.git_utils import push_to_git
from ..core.vector_db import VectorDBClient
from ..core.mcp_client import get_microsoft_docs_mcp, get_github_mcp, get_filesystem_mcp


def _strip_code_fences(text: str) -> str:
    if not text:
        return ""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z0-9_-]*", "", cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r"```$", "", cleaned, flags=re.MULTILINE)
    return cleaned.strip()


def _slugify(value: str, default: str = "scenario") -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower())
    value = re.sub(r"-+", "-", value).strip("-")
    return value or default


def _to_camel_case(value: str) -> str:
    if not value:
        return ""
    cleaned = re.sub(r"['\"_]+", " ", str(value))
    cleaned = re.sub(r"\s+", " ", cleaned).strip().lower()
    if not cleaned:
        return ""
    # Remove leading numbers to ensure valid identifier
    cleaned = re.sub(r"^[0-9]+", "", cleaned).strip()
    if not cleaned:
        return "Generated"
    # Convert to camelCase
    result = re.sub(r"[^a-z0-9]+(.)?", lambda m: m.group(1).upper() if m.group(1) else "", cleaned)
    # Ensure result doesn't start with a number (safety check)
    if result and result[0].isdigit():
        result = "Test" + result
    return result or "Generated"


def _urls_match(url1: str, url2: str) -> bool:
    """Compare two URLs ignoring query parameters and fragments."""
    from urllib.parse import urlparse
    
    if not url1 or not url2:
        return False
    
    parsed1 = urlparse(url1)
    parsed2 = urlparse(url2)
    
    # Compare scheme, netloc, and path (ignore query and fragment)
    return (parsed1.scheme == parsed2.scheme and 
            parsed1.netloc == parsed2.netloc and 
            parsed1.path == parsed2.path)


def _group_steps_by_page_title(steps: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Group steps by their pageTitle for page-based file organization."""
    grouped = {}
    for step in steps:
        page_title = step.get('pageTitle') or step.get('page_title') or 'Unknown'
        if page_title not in grouped:
            grouped[page_title] = []
        grouped[page_title].append(step)
    return grouped


def _scan_existing_pages(framework: "FrameworkProfile") -> List[str]:
    """Scan the framework's pages directory for existing page files."""
    if not framework.pages_dir or not framework.pages_dir.exists():
        return []
    
    existing_pages = []
    for file_path in framework.pages_dir.glob("*.ts"):
        page_name = file_path.stem
        existing_pages.append(page_name)
    
    return existing_pages


def _scan_existing_locators(framework: "FrameworkProfile") -> List[str]:
    """Scan the framework's locators directory for existing locator files."""
    if not framework.locators_dir or not framework.locators_dir.exists():
        return []
    
    existing_locators = []
    for file_path in framework.locators_dir.glob("*.ts"):
        locator_name = file_path.stem
        existing_locators.append(locator_name)
    
    return existing_locators


def _get_login_home_urls(framework: "FrameworkProfile") -> Dict[str, str]:
    """Extract URLs from existing login and home page files."""
    urls = {}
    
    if not framework.pages_dir or not framework.pages_dir.exists():
        return urls
    
    # Check for login page
    login_path = framework.pages_dir / "login.page.ts"
    if login_path.exists():
        try:
            content = login_path.read_text(encoding='utf-8')
            match = re.search(r"page\.goto\(['\"]([^'\"]+)['\"]", content)
            if match:
                urls['login'] = match.group(1)
        except Exception as e:
            logger.warning(f"Failed to read login page URL: {e}")
    
    # Check for home page
    home_path = framework.pages_dir / "home.page.ts"
    if home_path.exists():
        try:
            content = home_path.read_text(encoding='utf-8')
            match = re.search(r"page\.goto\(['\"]([^'\"]+)['\"]", content)
            if match:
                urls['home'] = match.group(1)
        except Exception as e:
            logger.warning(f"Failed to read home page URL: {e}")
    
    return urls


def _normalize_selector(selector: str) -> str:
    if not selector:
        return ""
    raw = str(selector).strip()
    
    # Check if it's a CSS selector with structural information (>, nth-child, etc.)
    # If so, preserve it as-is rather than simplifying to just an ID
    has_structure = any(marker in raw for marker in [' > ', ':nth-child(', ':nth-of-type(', ' + ', ' ~ '])
    
    # Only extract ID if there's no structural CSS and selector is just a simple ID reference
    hash_index = raw.find("#")
    if hash_index != -1 and not has_structure:
        fragment = raw[hash_index + 1 :]
        cut_index = re.search(r'[ \t\r\n>+~,.\[]', fragment)
        if cut_index:
            fragment = fragment[: cut_index.start()]
        fragment = fragment.strip()
        if fragment:
            escaped = fragment.replace('"', r"\"")
            return f'xpath=//*[@id="{escaped}"]'
    
    # Preserve CSS selectors with structure; just normalize whitespace
    normalized = re.sub(r"\|[a-zA-Z][\w-]*", "", raw)
    normalized = re.sub(r"\s+", " ", normalized)
    normalized = re.sub(r"\s*([>+~,])\s*", r"\1", normalized)
    normalized = normalized.strip()
    return normalized


def _extract_data_value(step: Dict[str, Any]) -> str:
    data = step.get("data")
    if isinstance(data, str):
        trimmed = data.strip()
        if not trimmed:
            return ""
        if ":" in trimmed:
            key, value = trimmed.split(":", 1)
            return value.strip()
        return trimmed
    return ""


def _extract_data_key(step: Dict[str, Any]) -> str:
    # Check if step has applyDataKeys from code generation (first candidate is the Excel column name)
    apply_data_keys = step.get("applyDataKeys")
    if apply_data_keys and isinstance(apply_data_keys, list) and len(apply_data_keys) > 0:
        return apply_data_keys[0]  # Return first candidate (Excel column name)
    
    # Fallback to original logic for backward compatibility
    data = step.get("data")
    if isinstance(data, str) and ":" in data:
        key, _ = data.split(":", 1)
        return key.strip()
    
    navigation = step.get("navigation")
    if isinstance(navigation, str):
        text = navigation.strip()
        
        # Clean up common prefixes and suffixes from recorded action text
        # Remove table/form prefixes like "Purchtable", "Inventtable", etc.
        text = re.sub(r'^[A-Z][a-z]+table\s+', '', text, flags=re.IGNORECASE)
        text = re.sub(r'^[A-Z][a-z]+form\s+', '', text, flags=re.IGNORECASE)
        
        # Remove "Field" suffix
        text = re.sub(r'\s+Field$', '', text, flags=re.IGNORECASE)
        
        # Extract meaningful field name from "Enter X" pattern
        match = re.search(r"enter\s+([a-z0-9 _-]+)", text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        # Return cleaned text
        return text.strip()
    
    return ""


def _step_signature(step: Dict[str, Any]) -> str:
    action = (step.get("action") or "").strip().lower()
    navigation = (step.get("navigation") or "").strip().lower()
    data = (step.get("data") or "").strip().lower()
    # Include step number to distinguish duplicate actions
    step_num = step.get("step", "")
    return f"{step_num}|{action}|{navigation}|{data}"


def _extract_preview_signatures(preview: str) -> Optional[Set[str]]:
    if not preview:
        return None
    signatures: Set[str] = set()
    parsed_count = 0
    for raw_line in preview.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        # Extract step number
        step_num = ""
        if line[0].isdigit():
            parts = line.split(" ", 1)
            if len(parts) == 2 and parts[0].rstrip('.').isdigit():
                step_num = parts[0].rstrip('.')
                line = parts[1].strip()
        if '|' not in line:
            continue
        segments = [segment.strip().lower() for segment in line.split("|")]
        if not segments:
            continue
        action = segments[0]
        navigation = segments[1] if len(segments) > 1 else ""
        data_value = ""
        for segment in segments[2:]:
            if segment.startswith("data:"):
                data_value = segment.split(":", 1)[1].strip()
        # Include step number in signature
        signature = f"{step_num}|{action}|{navigation}|{data_value}"
        signatures.add(signature)
        parsed_count += 1
    if parsed_count < 1:
        return None
    return signatures


def _normalize_for_match(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", (text or "").strip().lower())
    cleaned = cleaned.replace("'", "").replace('"', "")
    return cleaned


def _extract_preview_phrases(preview: str) -> Set[str]:
    """Collect normalized action/navigation phrases from the preview list.

    The preview format is expected to be pipe-separated columns like:
      Action | Navigation | Data: ... | Expected: ...
    We capture the first two segments (action, navigation) when present; otherwise, we use the whole line.
    """
    phrases: Set[str] = set()
    if not preview:
        return phrases
    for raw_line in preview.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        # Strip leading numbering like "19. "
        if line and line[0].isdigit():
            parts = line.split(" ", 1)
            if len(parts) == 2 and parts[0][:-1].isdigit() if parts[0].endswith('.') else parts[0].isdigit():
                line = parts[1].strip()
        if "|" in line:
            segments = [seg.strip() for seg in line.split("|")]
            if segments:
                phrases.add(_normalize_for_match(segments[0]))
            if len(segments) > 1:
                phrases.add(_normalize_for_match(segments[1]))
        else:
            phrases.add(_normalize_for_match(line))
    return {p for p in phrases if p}


def _relative_import(from_path: Path, to_path: Path) -> str:
    rel = os.path.relpath(to_path, start=from_path.parent)
    rel_posix = posixpath.normpath(rel.replace("\\", "/"))
    if not rel_posix.startswith("."):
        rel_posix = f"./{rel_posix}"
    return rel_posix


@dataclass
class FrameworkProfile:
    root: Path
    locators_dir: Optional[Path] = None
    pages_dir: Optional[Path] = None
    tests_dir: Optional[Path] = None
    additional_dirs: Dict[str, Path] = field(default_factory=dict)

    @classmethod
    def from_root(cls, root_path: str | Path) -> "FrameworkProfile":
        root = Path(root_path).expanduser().resolve()
        if not root.exists():
            raise FileNotFoundError(f"Framework repo not found: {root}")

        def find_dir(candidates: List[str]) -> Optional[Path]:
            for name in candidates:
                candidate = root / name
                if candidate.exists() and candidate.is_dir():
                    return candidate
            return None

        locators = find_dir(["locators", "locator", "selectors"])
        pages = find_dir(["pages", "page", "pageObjects", "page_objects", "src/pages"])
        tests = find_dir(["tests", "specs", "test", "e2e", "src/tests"])

        additional = {}
        for name in ["fixtures", "data", "util", "utils", "support"]:
            candidate = root / name
            if candidate.exists() and candidate.is_dir():
                additional[name] = candidate

        return cls(root=root, locators_dir=locators, pages_dir=pages, tests_dir=tests, additional_dirs=additional)

    def sample_snippet(self, directory: Optional[Path], limit_files: int = 2, max_chars: int = 1200) -> str:
        if not directory or not directory.exists():
            return ""

        snippets: List[str] = []
        for path in sorted(directory.glob("**/*.ts"))[:limit_files]:
            try:
                content = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            rel = path.relative_to(self.root)
            snippets.append(f"// {rel}\n{content}")
            if sum(len(s) for s in snippets) > max_chars:
                break
        combined = "\n\n".join(snippets)
        return combined[:max_chars]

    def summary(self) -> str:
        parts = [f"Root: {self.root}"]
        if self.locators_dir:
            parts.append(f"Locators dir: {self.locators_dir.relative_to(self.root)}")
        if self.pages_dir:
            parts.append(f"Pages dir: {self.pages_dir.relative_to(self.root)}")
        if self.tests_dir:
            parts.append(f"Tests dir: {self.tests_dir.relative_to(self.root)}")
        if self.additional_dirs:
            parts.append("Additional dirs: " + ", ".join(name for name in self.additional_dirs))
        return " | ".join(parts)


logger = logging.getLogger(__name__)


class AgenticScriptAgent:
    def __init__(self):
        # Lazy-initialize LLM to avoid failures in endpoints that don't require it (e.g., keyword-inspect)
        self.llm = None  # type: ignore[assignment]
        # Vector DB removed - using disk-based flow loading only
        # self.vector_db = VectorDBClient()
        # MCP clients for enhanced context
        self.microsoft_docs_mcp = get_microsoft_docs_mcp()
        self.github_mcp = get_github_mcp()
        self.filesystem_mcp = get_filesystem_mcp()
        # Single unified prompt for all LLM interactions
        self.unified_prompt = PromptTemplate(
            input_variables=[
                "task_type",
                "scenario",
                "recorded_steps",
                "reference_files",
                "flow_name",
                "start_url",
            ],
            template=(
                "You are a Playwright test automation expert. Generate production-ready TypeScript test files.\n\n"
                "TASK: {task_type}\n\n"
                "SCENARIO: {scenario}\n"
                "FLOW NAME: {flow_name}\n"
                "START URL: {start_url}\n\n"
                "═══════════════════════════════════════════════════════════════════════════════\n"
                "RECORDED STEPS FROM USER (with [Page Title] prefix):\n"
                "═══════════════════════════════════════════════════════════════════════════════\n"
                "{recorded_steps}\n\n"
                "═══════════════════════════════════════════════════════════════════════════════\n"
                "REFERENCE IMPLEMENTATION (YOUR TARGET STRUCTURE):\n"
                "═══════════════════════════════════════════════════════════════════════════════\n"
                "{reference_files}\n\n"
                "═══════════════════════════════════════════════════════════════════════════════\n"
                "CRITICAL REQUIREMENTS - MUST FOLLOW EXACTLY:\n"
                "═══════════════════════════════════════════════════════════════════════════════\n\n"
                "1. PAGE-BASED FILE STRUCTURE (MANDATORY):\n"
                "   ⚠️ DETECT UNIQUE PAGE TITLES FROM STEPS (e.g., [OneCognizant], [guidewire-hub - Sign In], [Guidewire Home])\n"
                "   ⚠️ CREATE SEPARATE FILES PER PAGE:\n"
                "   • locators/<PageTitle>.ts (e.g., locators/OneCognizant.ts)\n"
                "   • pages/<PageTitle>.pages.ts (e.g., pages/OneCognizant.pages.ts)\n"
                "   ⚠️ ONE TEST FILE: tests/{flow_name}.spec.ts\n"
                "   ⚠️ Test file MUST import ALL page classes and stitch them together in sequential steps\n\n"
                "2. LOCATOR STRATEGY (ALWAYS 2+ ATTRIBUTES - MANDATORY):\n"
                "   Priority 1: visible_text + playwright_property → page.getByRole('button', {{ name: 'Submit' }}).and(page.locator('[data-test=\"submit-btn\"]'))\n"
                "   Priority 2: visible_text + css → page.getByText('Submit').and(page.locator('button.submit-btn'))\n"
                "   Priority 3: playwright + css/xpath → page.getByRole('textbox', {{ name: 'Email' }}).and(page.locator('input[name=\"email\"]'))\n"
                "   Priority 4: css + html_attributes → page.locator('input[type=\"text\"][name=\"email\"][placeholder=\"Enter email\"]')\n"
                "   Priority 5: xpath + html → page.locator('xpath=//input[@type=\"text\" and @name=\"email\" and @placeholder=\"Enter email\"]')\n"
                "   ❌ NEVER use single-attribute selectors: page.locator('#email') ← WRONG\n"
                "   ✅ ALWAYS combine 2+ attributes for resilience\n\n"
                "3. PAGE CLASS STRUCTURE (MATCH REFERENCE EXACTLY):\n"
                "   • import {{ Page, Locator }} from '@playwright/test';\n"
                "   • import HelperClass from \"../util/methods.utility.ts\";\n"
                "   • import locators from \"../locators/<PageTitle>.ts\";\n"
                "   • Properties: page: Page, helper: HelperClass, ALL element Locators\n"
                "   • Constructor: Initialize helper, map ALL locators with page.locator(locators.elementName)\n"
                "   • Include: coerceValue, normaliseDataKey, resolveDataValue, applyData methods\n"
                "   • Setter methods for each input field (setSupplier, setNumber, setAmount, etc.)\n"
                "   • applyData method with fallbackValues and index support for duplicate fields\n\n"
                "4. TEST FILE STRUCTURE (MATCH REFERENCE EXACTLY):\n"
                "   • import {{ test }} from \"./testSetup.ts\";\n"
                "   • import ALL page classes: import OneCognizantPage from \"../pages/OneCognizant.pages.ts\";\n"
                "   • import LoginPage and HomePage\n"
                "   • import {{ getTestToRun, shouldRun, readExcelData }} from \"../util/csvFileManipulation.ts\";\n"
                "   • import {{ attachScreenshot, namedStep }} from \"../util/screenshot.ts\";\n"
                "   • test.beforeAll: executionList = getTestToRun(...)\n"
                "   • Declare ALL page instances: let oneCognizantPage: OneCognizantPage;\n"
                "   • Initialize in test: oneCognizantPage = new OneCognizantPage(page);\n"
                "   • Data handling: Read from Excel with ReferenceID, DatasheetName, IDName\n"
                "   • Each step: await namedStep(\"Step X - Action\", page, testinfo, async () => {{ ... }})\n"
                "   • Screenshot after EVERY step: attachScreenshot(\"Step X\", testinfo, screenshot)\n\n"
                "5. DATA MAPPING (CRITICAL):\n"
                "   ✅ CORRECT: await createinvoicepayablespage.applyData(dataRow, [\"Supplier\"], 0)\n"
                "   ✅ CORRECT: const val = getDataValue('BusinessUnit', 'FU01'); await page.getByText(val).click()\n"
                "   ✅ CORRECT: await page.applyData(dataRow, [\"Amount\"], 1) // for 2nd Amount field\n"
                "   ❌ WRONG: await page.supplier.fill('Allied Manufacturing') // hardcoded value\n"
                "   ❌ WRONG: await page.alliedManufacturing10001.click() // hardcoded element\n\n"
                "6. OUTPUT FORMAT (STRICT JSON):\n"
                "   Return ONLY valid JSON (no markdown fences, no explanations):\n"
                "   {{\n"
                "     \"locators/<PageTitle1>.ts\": \"<complete TypeScript code>\",\n"
                "     \"locators/<PageTitle2>.ts\": \"<complete TypeScript code>\",\n"
                "     \"pages/<PageTitle1>.pages.ts\": \"<complete TypeScript code>\",\n"
                "     \"pages/<PageTitle2>.pages.ts\": \"<complete TypeScript code>\",\n"
                "     \"tests/{flow_name}.spec.ts\": \"<complete TypeScript code>\"\n"
                "   }}\n\n"
                "⚠️ MUST GENERATE:\n"
                "• Separate locator file per unique page title\n"
                "• Separate page file per unique page title\n"
                "• One test file that imports and uses ALL page classes\n"
                "• Every locator MUST have 2+ attributes (NEVER single attribute)\n"
                "• Test data MUST use applyData() or getDataValue() (NEVER hardcoded values)\n\n"
                "Generate complete, production-ready code. NO placeholders. NO TODOs. NO comments like '// Add more locators'.\n"
            ),
        )
    def _ensure_llm(self):
        """Instantiate the LLM only when needed (preview/refine).
        Defaults to Copilot endpoints. Falls back to Azure OpenAI only if Copilot is not available.
        """
        if self.llm is None:
            # Default to Copilot bridge (http://localhost:3030 if not set)
            copilot_url = os.getenv("COPILOT_BRIDGE_URL", "http://localhost:3030")
            try:
                # Always try Copilot first
                from ..core.llm_client_copilot import CopilotClient
                self.llm = CopilotClient(temperature=0.2)
                logger.info("✓ Using Copilot endpoint at %s", copilot_url)
            except Exception as copilot_error:
                # Fall back to Azure OpenAI only if Copilot fails
                logger.warning(f"Copilot endpoint unavailable ({copilot_error}), falling back to Azure OpenAI")
                if AzureChatOpenAI is None:
                    raise RuntimeError("Neither Copilot nor AzureChatOpenAI available; install langchain-openai or configure Copilot")
                missing = [
                    var for var in [
                        "OPENAI_API_VERSION",
                        "AZURE_OPENAI_DEPLOYMENT",
                        "AZURE_OPENAI_ENDPOINT",
                        "AZURE_OPENAI_KEY",
                    ]
                    if not os.getenv(var)
                ]
                if missing:
                    raise RuntimeError(f"Missing Azure OpenAI env vars: {', '.join(missing)}")
                self.llm = AzureChatOpenAI(
                    openai_api_version=os.getenv("OPENAI_API_VERSION"),
                    azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT", "GPT-4o"),
                    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
                    api_key=os.getenv("AZURE_OPENAI_KEY"),
                    temperature=0.2,
                )
                logger.info("Using Azure OpenAI (fallback)")
        return self.llm

    def gather_context(self, scenario: str) -> Dict[str, Any]:
        # Orchestrator removed - context gathering now done via vector DB only
        # try:
        #     existing_script, recorder_flow, ui_crawl, test_case, structure, enriched_steps = (
        #         self.orchestrator.generate_script(scenario)
        #     )
        # except Exception as exc:
        #     # Don't let context gathering break endpoints that can work with vector/FS only
        #     logger.warning("orchestrator.generate_script failed for scenario '%s': %s", scenario, exc)
        existing_script, recorder_flow, ui_crawl, test_case, structure, enriched_steps = (
            None, None, None, None, None, None
        )

        enriched_text = json.dumps(enriched_steps, indent=2) if enriched_steps else ""
        existing_excerpt = ""
        if existing_script and existing_script.get("content"):
            existing_excerpt = str(existing_script["content"])[:1200]

        vector_steps = self._collect_vector_flow_steps(scenario)
        vector_flow_name = vector_steps[0].get("flow_name") if vector_steps else ""
        vector_flow_slug = vector_steps[0].get("flow_slug") if vector_steps else ""
        if vector_steps:
            enriched_text = self._format_steps_for_prompt(vector_steps)

        scaffold_snippet = self._fetch_scaffold_snippet(scenario)

        return {
            "enriched_steps": enriched_text,
            "existing_script_excerpt": existing_excerpt,
            "scaffold_snippet": scaffold_snippet,
            "vector_steps": vector_steps,
            "artifacts": {
                "existing_script": existing_script,
                "recorder_flow": recorder_flow,
                "ui_crawl": ui_crawl,
                "test_case": test_case,
                "structure": structure,
            },
            "flow_available": bool(recorder_flow) or bool(vector_steps),
            "vector_flow": {
                "flow_name": vector_flow_name,
                "flow_slug": vector_flow_slug,
            } if vector_flow_name or vector_flow_slug else None,
        }

    def generate_preview(self, scenario: str, framework: FrameworkProfile, context: Dict[str, Any]) -> str:
        logger.info(f"[Preview] Starting preview generation for scenario: {scenario}")
        
        enriched = context.get("enriched_steps", "").strip()
        vector_steps = context.get("vector_steps") or []
        
        if not enriched and not vector_steps:
            logger.warning("[Preview] No contextual steps found - returning INSUFFICIENT_CONTEXT")
            return (
                "INSUFFICIENT_CONTEXT: No recorder or vector-backed steps found. "
                "Please record the scenario or ingest relevant docs before generating a preview."
            )
        
        # Return formatted steps directly (no LLM needed for preview)
        if vector_steps:
            logger.info(f"[Preview] Returning {len(vector_steps)} vector steps")
            return self._format_steps_for_prompt(vector_steps)
        
        return enriched

    def refine_preview(
        self,
        scenario: str,
        framework: FrameworkProfile,
        previous_preview: str,
        feedback: str,
        context: Dict[str, Any],
    ) -> str:
        # Refine is not needed - just return previous preview
        # User can manually edit the preview in the UI
        return previous_preview

    @staticmethod
    def _scenario_variants(scenario: str) -> Tuple[List[str], List[str]]:
        """Derive likely flow names and slugs from a free-form scenario request."""
        raw = (scenario or "").strip()
        if not raw:
            return [], []

        variants: List[str] = []
        seen_lower: set[str] = set()

        def _add_variant(text: str) -> None:
            cleaned = (text or "").strip(" -:,\n\t")
            if not cleaned:
                return
            lowered = cleaned.lower()
            if lowered not in seen_lower:
                seen_lower.add(lowered)
                variants.append(cleaned)

        _add_variant(raw)

        prefixes = [
            "generate automation script for",
            "generate test script for",
            "create automation script for",
            "create test script for",
            "automation script for",
            "automation scripts for",
            "automation for",
            "test scripts for",
            "test script for",
            "test cases for",
            "test case for",
            "script for",
            "scripts for",
        ]

        working = raw
        lowered = working.lower()
        for prefix in sorted(prefixes, key=len, reverse=True):
            if lowered.startswith(prefix):
                working = working[len(prefix) :].strip(" -:,\n\t")
                _add_variant(working)
                lowered = working.lower()
                break

        cleanup_patterns = [
            r"\bfrom\s+refined\s+recorder\s+flow\b",
            r"\bfrom\s+refined\s+flow\b",
            r"\bfrom\s+recorder\s+flow\b",
            r"\brefined\s+recorder\s+flow\b",
            r"\brefined\s+flow\b",
            r"\brecorder\s+flow\b",
            r"\bagentic\s+flow\b",
        ]
        cleaned = working
        for pattern in cleanup_patterns:
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE).strip(" -:,\n\t")

        trailing_suffixes = [
            " ui",
            " flow",
            " flows",
            " scenario",
            " test",
            " script",
        ]
        lower_cleaned = cleaned.lower()
        for suffix in trailing_suffixes:
            if lower_cleaned.endswith(suffix):
                cleaned = cleaned[: -len(suffix)].strip(" -:,\n\t")
                lower_cleaned = cleaned.lower()
                break

        _add_variant(cleaned)

        # Include a variant with the last segment after "for" if any text remains noisy.
        if " for " in raw.lower():
            tail = raw.lower().split(" for ", 1)[-1]
            _add_variant(tail)

        slug_variants: List[str] = []
        seen_slugs: set[str] = set()
        for text in variants:
            slug = _slugify(text)
            if slug and slug not in seen_slugs:
                slug_variants.append(slug)
                seen_slugs.add(slug)

        return variants, slug_variants

    @staticmethod
    def _select_best_slug(slug_hits: Counter, preferred_slugs: List[str]) -> Optional[str]:
        if not slug_hits:
            return None
        preferred_lower = [s.lower() for s in preferred_slugs]

        def _score(slug: str) -> Tuple[int, int]:
            try:
                idx = preferred_lower.index(slug.lower())
            except ValueError:
                idx = len(preferred_lower)
            return slug_hits[slug], -idx

        best = max(slug_hits, key=_score)
        return best if slug_hits[best] > 0 else None

    def _steps_from_vector_docs(
        self,
        docs: List[Dict[str, Any]],
        default_flow_slug: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        steps_map: Dict[int, Dict[str, str]] = {}
        resolved_name: Optional[str] = None
        resolved_slug = _slugify(default_flow_slug) if default_flow_slug else None
        resolved_original_url: Optional[str] = None
        for entry in docs or []:
            meta = (entry or {}).get("metadata") or {}
            record_kind = str(meta.get("record_kind") or "").lower()
            if record_kind and record_kind != "step":
                continue
            content = self._parse_content_snapshot(entry.get("content") or "")
            payload = content.get("payload") if isinstance(content, dict) else {}
            step_index = meta.get("step_index") or (payload or {}).get("step_index")
            try:
                step_no = int(step_index)
            except (TypeError, ValueError):
                continue
            action = (meta.get("action") or (payload or {}).get("action") or "").strip()
            navigation = (meta.get("navigation") or (payload or {}).get("navigation") or "").strip()
            data_val = (meta.get("data") or (payload or {}).get("data") or "").strip()
            expected = (meta.get("expected") or (payload or {}).get("expected") or "").strip()
            # Do not drop steps without action/navigation; preserve numbering for preview continuity
            flow_slug = meta.get("flow_slug") or (payload or {}).get("flow_slug") or resolved_slug or ""
            flow_name = meta.get("flow_name") or (payload or {}).get("flow") or resolved_name or ""
            original_url = meta.get("original_url") or (payload or {}).get("original_url") or resolved_original_url or ""
            resolved_name = flow_name or resolved_name
            resolved_slug = _slugify(flow_slug) if flow_slug else resolved_slug
            resolved_original_url = original_url or resolved_original_url
            locator_info = (payload or {}).get("locators") or {}
            element_info = (payload or {}).get("element") or {}
            steps_map[step_no] = {
                "step": step_no,
                "action": action,
                "navigation": navigation,
                "data": data_val,
                "expected": expected,
                "flow_name": flow_name,
                "flow_slug": resolved_slug,
                "locators": locator_info,
                "element": element_info,
                "original_url": resolved_original_url or "",
            }
        return [steps_map[idx] for idx in sorted(steps_map)]

    def _load_refined_flow_from_disk(
        self,
        slug_candidates: List[str],
        name_candidates: List[str],
    ) -> List[Dict[str, str]]:
        # generated_flows is in app/, not app/generators/
        generated_dir = Path(__file__).resolve().parent.parent / "generated_flows"
        logger.info(f"[Disk Load] Generated flows directory: {generated_dir}")
        logger.info(f"[Disk Load] Directory exists: {generated_dir.exists()}")
        if not generated_dir.exists():
            logger.warning(f"[Disk Load] generated_flows directory does not exist: {generated_dir}")
            return []
        
        logger.info(f"[Disk Load] Searching for flow with slug_candidates={slug_candidates}, name_candidates={name_candidates}")
        
        slug_lower = [s.lower() for s in slug_candidates if s]
        name_lower = [n.lower() for n in name_candidates if n]
        try:
            candidates = sorted(
                generated_dir.glob("*.refined.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            logger.info(f"[Disk Load] Found {len(candidates)} .refined.json files")
        except Exception as e:
            logger.error(f"[Disk Load] Failed to glob files: {e}")
            return []
        
        for path in candidates:
            # Remove .refined suffix from stem for matching
            stem = path.stem
            if stem.endswith('.refined'):
                stem = stem[:-len('.refined')]
            stem_lower = stem.lower()
            logger.info(f"[Disk Load] Checking file: {path.name}, stem_lower: {stem_lower}")
            logger.debug(f"[Disk Load] Checking file: {path.name}")
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning(f"[Disk Load] Failed to parse {path.name}: {e}")
                continue
            
            flow_name = str(data.get("flow_name") or path.stem)
            flow_slug = _slugify(flow_name)
            
            logger.info(f"[Disk Load]   File: {path.name} -> flow_name={flow_name}, flow_slug={flow_slug}")
            logger.info(f"[Disk Load]   Comparing: flow_slug.lower()={flow_slug.lower()} against slug_lower={slug_lower}")
            logger.debug(f"[Disk Load]   File: {path.name} -> flow_name='{flow_name}', flow_slug='{flow_slug}'")
            
            # Check if this flow matches our search criteria
            matches = False
            if slug_lower and flow_slug.lower() in slug_lower:
                matches = True
                logger.info(f"[Disk Load]   ✓ Matched by flow_slug: {flow_slug}")
            elif any(slug in stem_lower for slug in slug_lower):
                matches = True
                logger.info(f"[Disk Load]   ✓ Matched by stem: {stem_lower}")
            elif name_lower and flow_name.lower() in name_lower:
                matches = True
                logger.info(f"[Disk Load]   ✓ Matched by flow_name: {flow_name}")
            
            if not matches:
                logger.debug(f"[Disk Load]   ✗ No match for {path.name}")
                continue
            
            steps = data.get("steps") or []
            # Extract original_url and pages metadata from top-level
            original_url = str(data.get("original_url") or "").strip()
            pages_metadata = data.get("pages") or {}
            
            # Build URL to page title mapping and pageId to page info mapping
            url_to_title = {}
            pageid_to_info = {}
            
            # Handle both dict and list formats for pages
            if isinstance(pages_metadata, dict):
                logger.info(f"[Disk Load] Processing pages dict with {len(pages_metadata)} entries")
                # Dictionary format: {page_id: {pageUrl, title, ...}}
                for page_id, page_meta in pages_metadata.items():
                    if isinstance(page_meta, dict):
                        page_url = page_meta.get("url") or page_meta.get("pageUrl") or ""
                        page_title = page_meta.get("title") or page_meta.get("pageTitle") or ""
                        logger.info(f"[Disk Load]   Page {page_id}: url={page_url[:50] if page_url else 'none'}, title={page_title}")
                        if page_url and page_title:
                            url_to_title[page_url] = page_title
                        if page_id:
                            pageid_to_info[page_id] = {"url": page_url, "title": page_title}
            elif isinstance(pages_metadata, list):
                logger.info(f"[Disk Load] Processing pages list with {len(pages_metadata)} entries")
                # List format: [{pageId, pageUrl, title, ...}]
                for page_meta in pages_metadata:
                    if isinstance(page_meta, dict):
                        page_url = page_meta.get("pageUrl") or page_meta.get("url") or ""
                        page_title = page_meta.get("pageTitle") or page_meta.get("title") or ""
                        page_id = page_meta.get("pageId") or ""
                        if page_url and page_title:
                            url_to_title[page_url] = page_title
                        if page_id:
                            pageid_to_info[page_id] = {"url": page_url, "title": page_title}
            
            logger.info(f"[Disk Load] Built mappings: {len(url_to_title)} URLs, {len(pageid_to_info)} page IDs")
            
            formatted: List[Dict[str, str]] = []
            for idx, step in enumerate(steps, start=1):
                step_no = step.get("step") or idx
                try:
                    step_no = int(step_no)
                except (TypeError, ValueError):
                    step_no = idx
                action = str(step.get("action") or "").strip()
                
                # Extract navigation from element if not already set
                navigation = str(step.get("navigation") or "").strip()
                if not navigation:
                    # Try to get from visibleText or element selector
                    visible_text = str(step.get("visibleText") or "").strip()
                    if visible_text:
                        navigation = visible_text
                    else:
                        element = step.get("element") or {}
                        if isinstance(element, dict):
                            selector = element.get("selector", {})
                            playwright_sel = selector.get("playwright", {})
                            # Extract from getByLabel, getByPlaceholder, getByText, etc.
                            for key, value in playwright_sel.items():
                                if value and isinstance(value, str):
                                    match = re.search(r"['\"]([^'\"]+)['\"]", value)
                                    if match:
                                        navigation = match.group(1)
                                        break
                            
                            # Fallback: Parse HTML element to extract meaningful context
                            if not navigation:
                                html = element.get("html", "")
                                if html and isinstance(html, str):
                                    # Try to extract from common attributes (ordered by priority)
                                    # 1. value attribute (for buttons and inputs)
                                    value_match = re.search(r'value=["\']([^"\']+)["\']', html)
                                    if value_match and value_match.group(1).strip():
                                        navigation = value_match.group(1).strip()
                                    
                                    # 2. aria-label attribute
                                    if not navigation:
                                        aria_match = re.search(r'aria-label=["\']([^"\']+)["\']', html)
                                        if aria_match and aria_match.group(1).strip():
                                            navigation = aria_match.group(1).strip()
                                    
                                    # 3. placeholder attribute
                                    if not navigation:
                                        placeholder_match = re.search(r'placeholder=["\']([^"\']+)["\']', html)
                                        if placeholder_match and placeholder_match.group(1).strip():
                                            navigation = placeholder_match.group(1).strip()
                                    
                                    # 4. name attribute (for form fields like "username")
                                    if not navigation:
                                        name_match = re.search(r'name=["\']([^"\']+)["\']', html)
                                        if name_match and name_match.group(1).strip():
                                            name_val = name_match.group(1).strip()
                                            # Make it more readable: "username" -> "username field"
                                            if name_val and not name_val.endswith('field'):
                                                navigation = f"{name_val} field"
                                            else:
                                                navigation = name_val
                                    
                                    # 5. data-type attribute (like "save")
                                    if not navigation:
                                        data_type_match = re.search(r'data-type=["\']([^"\']+)["\']', html)
                                        if data_type_match and data_type_match.group(1).strip():
                                            navigation = data_type_match.group(1).strip()
                                    
                                    # 6. type attribute as last resort (like "submit", "button")
                                    if not navigation:
                                        type_match = re.search(r'type=["\']([^"\']+)["\']', html)
                                        if type_match and type_match.group(1).strip():
                                            type_val = type_match.group(1).strip()
                                            # Only use meaningful types
                                            if type_val in ["submit", "button", "reset"]:
                                                navigation = f"{type_val} button"
                                            elif type_val in ["text", "email", "password", "search", "tel", "url"]:
                                                navigation = f"{type_val} input"
                
                data_val = str(step.get("data") or "").strip()
                expected = str(step.get("expected") or "").strip()
                locators = step.get("locators") or {}
                if not isinstance(locators, dict):
                    locators = {}
                element = step.get("element") or {}
                if not isinstance(element, dict):
                    element = {}
                
                # Get page title from step directly, or map via pageId/URL
                # Steps from the recorder already have pageTitle field
                page_title = str(step.get("pageTitle") or "").strip()
                page_url = str(step.get("pageUrl") or "").strip()
                page_id = str(step.get("pageId") or "").strip()
                
                # Only use mapping if pageTitle is empty or "Unknown"
                if not page_title or page_title == "Unknown":
                    # Use pageId mapping if available
                    if page_id and page_id in pageid_to_info:
                        page_title = pageid_to_info[page_id]["title"]
                        if not page_url:
                            page_url = pageid_to_info[page_id]["url"]
                    else:
                        # Fallback to URL mapping
                        page_title = url_to_title.get(page_url) or "Unknown"
                
                # Preserve steps even if action/navigation are empty to avoid gaps in numbering
                formatted.append(
                    {
                        "step": step_no,
                        "action": action,
                        "navigation": navigation,
                        "data": data_val,
                        "expected": expected,
                        "flow_name": flow_name,
                        "flow_slug": flow_slug,
                        "locators": locators,
                        "element": element,
                        "original_url": original_url,
                        "pageUrl": page_url,
                        "pageTitle": page_title,
                    }
                )
            if formatted:
                return sorted(formatted, key=lambda item: item["step"])
        return []

    def _collect_vector_flow_steps(self, scenario: str, top_k: int = 256) -> List[Dict[str, str]]:
        """Load flow steps from disk only - Vector DB completely removed"""
        logger.info(f"[Disk Only] Loading flow steps for scenario '{scenario}' from generated_flows/")
        name_variants, slug_variants = self._scenario_variants(scenario)
        logger.info(f"[Disk Only] Name variants: {name_variants}")
        logger.info(f"[Disk Only] Slug variants: {slug_variants}")
        
        # Load from disk only - no vector DB
        disk_steps = self._load_refined_flow_from_disk(slug_variants, name_variants)
        
        if disk_steps:
            logger.info(f"✓ Loaded {len(disk_steps)} steps from disk for scenario '{scenario}'")
            return disk_steps
        
        # No fallback to vector DB - just return empty
        logger.warning(f"✗ No flow found on disk for scenario '{scenario}'. Please record the flow first.")
        return []

    @staticmethod
    def _format_steps_for_prompt(steps: List[Dict[str, str]]) -> str:
        lines = []
        for item in steps:
            step_no = item.get("step")
            nav = item.get("navigation") or ""
            action = item.get("action") or ""
            data_val = item.get("data") or ""
            expected = item.get("expected") or ""
            parts = [part for part in [action, nav] if part]
            if data_val:
                parts.append(f"Data: {data_val}")
            if expected:
                parts.append(f"Expected: {expected}")
            if not parts:
                # Fallback to element/locator hints if available; otherwise a placeholder
                el = item.get("element") or {}
                loc = item.get("locators") or {}
                hint = ""
                try:
                    if isinstance(el, dict):
                        hint = el.get("name") or el.get("title") or ""
                    if not hint and isinstance(loc, dict):
                        hint = loc.get("name") or loc.get("title") or ""
                except Exception:
                    hint = ""
                placeholder = f"Note: {hint}" if hint else "Note: Recorded step (no action/navigation)"
                parts = [placeholder]
            lines.append(f"{step_no}. " + " | ".join(parts))
        # Default: do not truncate preview steps. Allow optional cap via env PREVIEW_MAX_STEPS.
        try:
            from os import getenv as _getenv
            limit_raw = _getenv("PREVIEW_MAX_STEPS")
            limit: Optional[int]
            if limit_raw is None or str(limit_raw).strip() == "":
                limit = None  # unlimited by default
            else:
                lowered = str(limit_raw).strip().lower()
                if lowered in {"all", "unlimited", "none"}:
                    limit = None
                else:
                    n = int(lowered)
                    limit = None if n <= 0 else n
        except Exception:
            limit = None
        return "\n".join(lines if limit is None else lines[: max(1, limit)])

    def _fetch_scaffold_snippet(self, scenario: str, limit: int = 3, max_chars: int = 1500) -> str:
        try:
            results = self.vector_db.query_where(
                scenario,
                where={"type": "script_scaffold"},
                top_k=limit,
            )
        except Exception:
            results = []

        snippets: List[str] = []
        for entry in results or []:
            metadata = entry.get("metadata") or {}
            content_obj = self._parse_content_snapshot(entry.get("content", ""))
            path = metadata.get("file_path") or ""
            code = ""
            if isinstance(content_obj, dict):
                path = content_obj.get("filePath") or content_obj.get("path") or path
                code = content_obj.get("content") or content_obj.get("body") or ""
            elif isinstance(content_obj, list):
                for item in content_obj:
                    if isinstance(item, dict) and not code:
                        path = item.get("filePath") or path
                        code = item.get("content") or item.get("body") or ""
            if not code:
                code = str(entry.get("content") or "")
            snippet = ""
            if path:
                snippet += f"// {path}\n"
            snippet += code.strip()
            if snippet:
                snippets.append(snippet[:max_chars])
            if sum(len(s) for s in snippets) >= max_chars:
                break
        return "\n\n".join(snippets)[:max_chars]

    @staticmethod
    def _parse_content_snapshot(content: str) -> Optional[Dict[str, Any]]:
        if not content:
            return None
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass
        try:
            return ast.literal_eval(content)
        except (SyntaxError, ValueError):
            return None

    @staticmethod
    def _candidate_paths_from_metadata(metadata: Dict[str, Any], content_obj: Optional[Dict[str, Any]]) -> List[str]:
        candidates = []
        keys = [
            "file_path",
            "path",
            "filePath",
            "relative_path",
            "relativePath",
            "module_path",
            "modulePath",
        ]
        for key in keys:
            value = metadata.get(key)
            if value:
                candidates.append(str(value))
        if content_obj:
            for key in keys + ["name", "fileName", "filename"]:
                value = content_obj.get(key)
                if value:
                    candidates.append(str(value))
        return candidates

    @staticmethod
    def _normalize_relative_path(candidate: str) -> Optional[str]:
        if not candidate:
            return None
        normalized = candidate.replace("\\", "/")
        markers = ["/locators/", "/pages/", "/tests/", "/features/", "/steps/"]
        lowered = normalized.lower()
        for marker in markers:
            idx = lowered.rfind(marker)
            if idx != -1:
                rel = normalized[idx + 1 :]
                return rel
        if re.match(r"^[a-zA-Z]:", normalized):
            return None
        if normalized.startswith("/tmp"):
            return None
        return normalized

    def _locate_framework_file(
        self, framework: FrameworkProfile, metadata: Dict[str, Any], content_str: str
    ) -> Optional[Path]:
        content_obj = self._parse_content_snapshot(content_str)
        candidates = self._candidate_paths_from_metadata(metadata, content_obj)
        for candidate in candidates:
            normalized = candidate.replace("\\", "/")
            framework_root_norm = str(framework.root.resolve()).replace("\\", "/").lower()
            lowered = normalized.lower()
            if lowered.startswith(framework_root_norm):
                rel = normalized[len(framework_root_norm):].lstrip("/")
                target = (framework.root / Path(rel)).resolve()
                if target.exists():
                    return target
            rel = self._normalize_relative_path(normalized)
            if rel:
                target = (framework.root / Path(rel)).resolve()
                if target.exists():
                    return target
            name = Path(normalized).name
            if name:
                matches = list(framework.root.rglob(name))
                if matches:
                    return matches[0]
        if content_obj and "name" in content_obj:
            matches = list(framework.root.rglob(content_obj["name"]))
            if matches:
                return matches[0]
        return None

    def find_existing_framework_assets(
        self, scenario: str, framework: FrameworkProfile, top_k: int = 8
    ) -> List[Dict[str, Any]]:
        try:
            results = self.vector_db.query(scenario, top_k=top_k)
        except Exception as exc:
            logger.warning("vector_db.query failed for scenario '%s': %s", scenario, exc)
            results = []
        assets: List[Dict[str, Any]] = []
        min_score = 6  # threshold to avoid unrelated matches
        scenario_tokens = self._tokenize(scenario)
        scenario_terms = {tok for tok in scenario_tokens if tok}

        def _path_matches(path_obj: Path) -> bool:
            lowered = str(path_obj).lower()
            return any(term in lowered for term in scenario_terms)

        for entry in results:
            metadata = entry.get("metadata", {}) or {}
            meta_type = str(metadata.get("type", "")) + str(metadata.get("artifact_type", ""))
            if not any(token in meta_type.lower() for token in ["script", "scaffold", "locator", "page", "test"]):
                continue
            content_str = entry.get("content", "")
            path = self._locate_framework_file(framework, metadata, content_str)
            if path and path.exists():
                if scenario_terms and not _path_matches(path):
                    continue
                try:
                    file_content = path.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    file_content = ""
                score = self._compute_relevance_score(path, file_content, scenario_tokens)
                if score >= min_score:
                    assets.append({
                        "path": path,
                        "metadata": {**metadata, "relevance_score": score, "source": "vector+repo"},
                        "id": entry.get("id"),
                    })
        # Fallback: direct repo scan if vector search found nothing
        if not assets:
            assets = self._filesystem_search_assets(framework, scenario, max_results=top_k)
        return assets

    def _filesystem_search_assets(self, framework: FrameworkProfile, scenario: str, max_results: int = 8) -> List[Dict[str, Any]]:
        """Search the framework repo for likely matching files when vector DB has no hits.
        Heuristics: match by filename and file content tokens under tests/pages/locators.
        """
        root = framework.root
        search_dirs: List[Path] = []
        for d in [framework.tests_dir, framework.pages_dir, framework.locators_dir]:
            if d and d.exists():
                search_dirs.append(d)
        search_dirs.extend(framework.additional_dirs.values())
        if not search_dirs:
            search_dirs = [root]

        tokens = self._tokenize(scenario)
        slug = _slugify(scenario)
        slug_parts = self._tokenize(slug)

        candidates: List[Tuple[int, Path]] = []
        seen: set[Path] = set()
        min_score = 6
        penalty_terms = {"supplier", "receipt", "invoice", "arinvoice", "apinvoice", "ap", "po", "procurement"}

        for base in search_dirs:
            for path in base.rglob("*.ts"):
                if path in seen:
                    continue
                seen.add(path)
                score = 0
                name = path.name.lower()
                # Filename match
                for t in slug_parts + tokens:
                    if t and t in name:
                        score += 3
                # Content match (lightweight)
                try:
                    content = path.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    content = ""
                low = content.lower()
                # Exact phrase boost
                phrase = " ".join(tokens)
                if phrase and phrase in low:
                    score += 4
                # Token overlap
                for t in tokens[:6]:  # cap tokens for perf
                    if t and t in low:
                        score += 1
                # Domain penalty if unrelated terms appear but not in scenario tokens
                for p in penalty_terms:
                    if p in low and p not in tokens:
                        score -= 2
                # Prefer tests over pages/locators in tie
                try:
                    rel = path.relative_to(root)
                    rel_low = str(rel).lower()
                    if any(seg in rel_low for seg in ["/tests/", "/specs/", "/e2e/"]):
                        score += 1
                except Exception:
                    pass
                if score > 0:
                    candidates.append((score, path))

        candidates.sort(key=lambda x: x[0], reverse=True)
        # Apply threshold to avoid unrelated matches
        filtered = [
            (s, p)
            for s, p in candidates
            if s >= min_score and (not tokens or any(t in str(p).lower() for t in tokens))
        ]
        results: List[Dict[str, Any]] = []
        for score, p in filtered[:max_results]:
            results.append({
                "path": p,
                "metadata": {"source": "filesystem", "relevance_score": score},
                "id": None,
            })
        return results

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        return [tok for tok in re.split(r"[^a-zA-Z0-9]+", (text or "").lower()) if len(tok) >= 3]

    def _compute_relevance_score(self, path: Path, content: str, scenario_tokens: List[str]) -> int:
        """Compute a simple relevance score combining filename and content overlaps.
        Adds a boost for exact phrase and test locations; penalizes common unrelated domains.
        """
        name = path.name.lower()
        score = 0
        for t in scenario_tokens:
            if t in name:
                score += 3
        low = (content or "").lower()
        phrase = " ".join(scenario_tokens)
        if phrase and phrase in low:
            score += 4
        for t in scenario_tokens[:6]:
            if t in low:
                score += 1
        try:
            rel_low = str(path).lower()
            if any(seg in rel_low for seg in ["/tests/", "/specs/", "/e2e/"]):
                score += 1
        except Exception:
            pass
        penalty_terms = {"supplier", "receipt", "invoice", "arinvoice", "apinvoice", "ap", "po", "procurement"}
        for p in penalty_terms:
            if p in low and p not in scenario_tokens:
                score -= 2
        return score

    def generate_script_payload(
        self,
        scenario: str,
        framework: FrameworkProfile,
        accepted_preview: str,
    ) -> Dict[str, List[Dict[str, str]]]:
        """Generate script payload using LLM with page-based generation.
        
        Always uses LLM (Copilot) to generate test scripts. The LLM is instructed to:
        - Create separate locator and page files per page when multiple pages detected
        - Use pageTitle from steps to group actions by page
        - Generate imports between files correctly
        """
        context = self.gather_context(scenario)
        vector_steps = context.get("vector_steps") or []
        if not vector_steps:
            raise ValueError(
                "No refined recorder steps available for this scenario. "
                "Please ingest the refined flow or record the scenario again."
            )
        
        # Always use LLM-enhanced generation with page-based awareness
        logger.info("[LLM Generation] Starting LLM-enhanced page-based generation")
        
        # Call LLM to generate page-based scripts
        payload = self._generate_payload_with_templates(
            scenario=scenario,
            framework=framework,
            accepted_preview=accepted_preview,
            vector_steps=vector_steps,
            use_llm_enhancement=True
        )
        
        logger.info(f"[LLM Generation] ✓ Generated {len(payload.get('locators', []))} locators, {len(payload.get('pages', []))} pages, {len(payload.get('tests', []))} tests")
        return payload
    
    def _generate_payload_with_templates(
        self,
        scenario: str,
        framework: FrameworkProfile,
        accepted_preview: str,
        vector_steps: List[Dict[str, Any]],
        use_llm_enhancement: bool = True,  # ENABLED by default for intelligent code generation
    ) -> Dict[str, List[Dict[str, str]]]:
        """Generate script payload using templates with LLM enhancement and system prompt"""
        logger.info("[LLM-Enhanced Generation] Starting code generation with system prompt integration")
        
        from .framework_templates import FrameworkTemplate, LLMEnhancedGenerator
        
        # Extract flow name from scenario
        flow_name = scenario.split("for")[-1].strip() if "for" in scenario else scenario
        flow_name = flow_name.replace("automation script", "").replace("test script", "").strip()
        
        # Get start URL from first step if available
        start_url = vector_steps[0].get('pageUrl', '') if vector_steps else ''
        
        # Use LLM-enhanced generation with system prompt
        if use_llm_enhancement:
            logger.info("[LLM Enhancement] ENABLED - Using Copilot with system prompt")
            try:
                llm = self._ensure_llm()
                
                # Load comprehensive template from file
                template_path = Path(__file__).resolve().parent.parent.parent / "generator" / ".md"
                system_prompt = ""
                if template_path.exists():
                    system_prompt = template_path.read_text(encoding='utf-8')
                    logger.info(f"[LLM Enhancement] Loaded template: {len(system_prompt)} chars")
                else:
                    logger.warning(f"[LLM Enhancement] Template not found at {template_path}")
                    # Fallback to old system prompt
                    fallback_path = Path(__file__).resolve().parent.parent.parent / "generator" / "SYSTEM_PROMPT_WITH_REFERENCES.md"
                    if fallback_path.exists():
                        system_prompt = fallback_path.read_text(encoding='utf-8')
                        logger.info(f"[LLM Enhancement] Loaded fallback prompt: {len(system_prompt)} chars")
                
                # Read reference files for context
                reference_page = ""
                reference_test = ""
                reference_locator = ""
                
                if framework and framework.pages_dir:
                    ref_page_path = framework.pages_dir / "CreateinvoicepayablesPage.ts"
                    if ref_page_path.exists():
                        reference_page = ref_page_path.read_text(encoding='utf-8')
                        logger.info(f"[LLM Enhancement] Loaded reference page: {len(reference_page)} chars")
                
                if framework and framework.tests_dir:
                    ref_test_path = framework.tests_dir / "create-invoice-payables.spec.ts"
                    if ref_test_path.exists():
                        reference_test = ref_test_path.read_text(encoding='utf-8')
                        logger.info(f"[LLM Enhancement] Loaded reference test: {len(reference_test)} chars")
                
                if framework and framework.locators_dir:
                    ref_locator_path = framework.locators_dir / "create-invoice-payables.ts"
                    if ref_locator_path.exists():
                        reference_locator = ref_locator_path.read_text(encoding='utf-8')
                        logger.info(f"[LLM Enhancement] Loaded reference locator: {len(reference_locator)} chars")
                
                # Format steps for prompt - include pageTitle for page-based generation
                steps_text = "\n".join([
                    f"Step {i+1}: [{step.get('pageTitle', 'Unknown Page')}] {step.get('action', '')} | {step.get('navigation', '')} | Data: {step.get('data', '')}"
                    for i, step in enumerate(vector_steps)
                ])
                
                # Detect unique pages for page-based generation instruction
                page_titles = set(step.get('pageTitle', 'Unknown') for step in vector_steps)
                page_titles.discard('Unknown')
                if len(page_titles) >= 2:
                    logger.info(f"[LLM Generation] Multiple pages detected: {sorted(page_titles)}")
                    logger.info(f"[LLM Generation] LLM will be instructed to create separate files per page")
                
                # Build reference files section
                reference_section = ""
                if reference_page:
                    reference_section += f"**Page File Example:**\n```typescript\n{reference_page[:2000]}\n```\n\n"
                if reference_test:
                    reference_section += f"**Test File Example:**\n```typescript\n{reference_test[:2000]}\n```\n\n"
                if reference_locator:
                    reference_section += f"**Locator File Example:**\n```typescript\n{reference_locator[:800]}\n```\n"
                
                # Use unified prompt
                prompt = self.unified_prompt.format(
                    task_type="Generate complete Playwright test files (locators, page, test)",
                    scenario=scenario,
                    recorded_steps=steps_text,
                    reference_files=reference_section or "Use standard Playwright patterns",
                    flow_name=flow_name,
                    start_url=start_url or "(will be extracted from steps)",
                )
                
                logger.info(f"[LLM Enhancement] Sending prompt to LLM: {len(prompt)} chars")
                logger.info(f"[LLM Enhancement] Flow name: {flow_name}, Start URL: {start_url}")
                response = llm.invoke(prompt)
                response_text = _strip_code_fences(getattr(response, "content", str(response)))
                logger.info(f"[LLM Enhancement] Received response: {len(response_text)} chars")
                logger.info(f"[LLM Enhancement] Response preview: {response_text[:200]}...")
                
                # Parse JSON response
                try:
                    # Try to extract JSON if wrapped in markdown
                    if '```json' in response_text:
                        json_start = response_text.find('```json') + 7
                        json_end = response_text.find('```', json_start)
                        response_text = response_text[json_start:json_end].strip()
                    elif '```' in response_text:
                        json_start = response_text.find('```') + 3
                        json_end = response_text.find('```', json_start)
                        response_text = response_text[json_start:json_end].strip()
                    
                    all_files = json.loads(response_text)
                    logger.info(f"[LLM Enhancement] ✓ Successfully parsed {len(all_files)} files from LLM")
                    logger.info(f"[LLM Enhancement] File keys: {list(all_files.keys())}")
                except json.JSONDecodeError as e:
                    logger.error(f"[LLM Enhancement] Failed to parse JSON: {e}")
                    logger.error(f"[LLM Enhancement] Response text: {response_text[:1000]}")
                    raise ValueError(f"LLM returned invalid JSON: {e}")
                
            except Exception as e:
                logger.error(f"[LLM Enhancement] ✗ Failed: {e}, falling back to static templates")
                # Fallback to static templates
                all_files = FrameworkTemplate.generate_all_files(
                    flow_name=flow_name,
                    steps=vector_steps,
                    start_url=start_url,
                    scenario=scenario
                )
        else:
            # Use static templates (default - no LLM needed)
            logger.info("[Static Templates] Generating code from templates (no LLM)")
            all_files = FrameworkTemplate.generate_all_files(
                flow_name=flow_name,
                steps=vector_steps,
                start_url=start_url,
                scenario=scenario
            )
        
        # Convert to expected payload format
        payload = {}
        logger.info(f"[LLM Enhancement] Converting {len(all_files)} files to payload format")
        logger.info(f"[LLM Enhancement] File keys from LLM: {list(all_files.keys())}")
        
        for file_path, content in all_files.items():
            logger.info(f"[LLM Enhancement] Processing file: {file_path}")
            
            # Determine directory from file path
            if '/' in file_path:
                dir_name = file_path.split('/')[0]
                file_name = file_path.split('/', 1)[1]
            else:
                # Fallback: guess directory from file extension
                if file_path.endswith('.spec.ts'):
                    dir_name = 'tests'
                    file_name = file_path
                elif 'Page.ts' in file_path or file_path.endswith('page.ts'):
                    dir_name = 'pages'
                    file_name = file_path
                else:
                    dir_name = 'locators'
                    file_name = file_path
            
            logger.info(f"[LLM Enhancement] Mapped to: {dir_name}/{file_name}")
            
            if dir_name not in payload:
                payload[dir_name] = []
            
            # Keep the directory prefix in the path for frontend filtering
            full_path = f"{dir_name}/{file_name}" if '/' not in file_name else file_name
            
            payload[dir_name].append({
                "path": full_path,
                "content": content
            })
            logger.info(f"[LLM Enhancement] Added to payload['{dir_name}'] with path '{full_path}' - {len(content)} chars")
        
        # Extract test data mapping from generated TEST files (applyData calls)
        test_data_mapping = []
        import re
        
        # Extract from test files by parsing applyData() calls
        for file_path, content in all_files.items():
            if '/tests/' in file_path or file_path.startswith('tests/') or file_path.endswith('.spec.ts'):
                # Pattern: await page.applyData(dataRow, ["ColumnName", "Alias1", "Alias2"], index)
                # We want to extract the first element of the array (the primary column name)
                apply_data_pattern = r'await\s+\w+\.applyData\(dataRow,\s*\[([^\]]+)\](?:,\s*(\d+))?\)'
                matches = re.findall(apply_data_pattern, content)
                
                for column_list_str, index_str in matches:
                    # Parse the column names array
                    column_names = re.findall(r'["\']([^"\']+)["\']', column_list_str)
                    if not column_names:
                        continue
                    
                    # First element is the primary Excel column name
                    primary_column = column_names[0]
                    
                    # Check if this column already exists
                    existing = next((m for m in test_data_mapping if m['columnName'] == primary_column), None)
                    if existing:
                        existing['occurrences'] += 1
                    else:
                        test_data_mapping.append({
                            'columnName': primary_column,
                            'occurrences': 1,
                            'actionType': 'fill',  # Default to fill, can be refined later
                            'methods': ['applyData']  # Actual method used in code
                        })
        
        # If no mappings found from test files, extract from page files as fallback
        if not test_data_mapping:
            logger.info("[Test Data Mapping] No applyData calls found in test files, extracting from page files")
            for file_path, content in all_files.items():
                if '/pages/' in file_path or file_path.startswith('pages/'):
                    # Extract from applyData method's fallbackValues
                    fallback_pattern = r'const fallbackValues: Record<string, string> = \{([^}]+)\}'
                    fallback_match = re.search(fallback_pattern, content, re.DOTALL)
                    if fallback_match:
                        fallback_content = fallback_match.group(1)
                        # Extract column names from "ColumnName": "" entries
                        column_matches = re.findall(r'["\']([^"\']+)["\']\s*:', fallback_content)
                        for column_name in column_matches:
                            if column_name not in [m['columnName'] for m in test_data_mapping]:
                                test_data_mapping.append({
                                    'columnName': column_name,
                                    'occurrences': 1,
                                    'actionType': 'fill',
                                    'methods': ['applyData']
                                })
        
        payload['testDataMapping'] = test_data_mapping
        logger.info(f"[LLM Enhancement] Final payload: {list(payload.keys())}")
        logger.info(f"[LLM Enhancement] Generated {len(all_files)} files with {len(test_data_mapping)} data mappings")
        return payload
    
    def _generate_payload_with_llm(
        self,
        scenario: str,
        framework: FrameworkProfile,
        accepted_preview: str,
        context: Dict[str, Any],
    ) -> Dict[str, List[Dict[str, str]]]:
        """Generate script payload using LLM instead of deterministic templates."""
        logger.info("[LLM Payload] Generating payload using Copilot LLM")
        
        slug = _slugify(scenario)
        locators_snippet = framework.sample_snippet(framework.locators_dir, limit_files=2, max_chars=800)
        pages_snippet = framework.sample_snippet(framework.pages_dir, limit_files=2, max_chars=800)
        tests_snippet = framework.sample_snippet(framework.tests_dir, limit_files=2, max_chars=800)
        
        prompt = self.script_prompt.format(
            scenario=scenario,
            accepted_preview=accepted_preview,
            framework_summary=framework.summary(),
            locators_snippet=locators_snippet,
            pages_snippet=pages_snippet,
            tests_snippet=tests_snippet,
            slug=slug,
        )
        
        try:
            llm = self._ensure_llm()
            logger.info("[LLM Payload] Sending request to LLM")
            response = llm.invoke(prompt)
            response_text = _strip_code_fences(getattr(response, "content", str(response)))
            logger.info(f"[LLM Payload] Received response: {len(response_text)} chars")
            
            # Parse JSON response
            try:
                payload = json.loads(response_text)
                logger.info(f"[LLM Payload] Parsed payload: {list(payload.keys())}")
                return payload
            except json.JSONDecodeError as e:
                logger.error(f"[LLM Payload] Failed to parse JSON: {e}")
                logger.error(f"[LLM Payload] Response text: {response_text[:500]}")
                raise ValueError(f"LLM returned invalid JSON: {e}")
        except Exception as exc:
            logger.error(f"[LLM Payload] Failed: {exc}")
            # Fallback to deterministic generation
            logger.warning("[LLM Payload] Falling back to deterministic generation")
            vector_steps = context.get("vector_steps") or []
            return self._build_deterministic_payload(scenario, framework, vector_steps, keep_signatures=None)

    @staticmethod
    def _generate_html_css_combo(css_selector: str, element_html: str, step: Dict[str, Any]) -> str:
        """Generate CSS selector enhanced with HTML element details.
        
        Args:
            css_selector: Base CSS selector
            element_html: HTML string of the element
            step: Step dictionary with additional context
            
        Returns:
            Enhanced CSS selector with multiple element details
        """
        import re
        
        # Extract multiple attributes from HTML
        attributes = {}
        attr_patterns = {
            'name': r'name="([^"]+)"',
            'id': r'id="([^"]+)"',
            'class': r'class="([^"]+)"',
            'placeholder': r'placeholder="([^"]+)"',
            'aria-label': r'aria-label="([^"]+)"',
            'type': r'type="([^"]+)"',
            'value': r'value="([^"]+)"'
        }
        
        for attr_name, pattern in attr_patterns.items():
            match = re.search(pattern, element_html)
            if match:
                attributes[attr_name] = match.group(1)
        
        # Build enhanced selector with multiple attributes
        enhanced_parts = [css_selector]
        
        if attributes.get('id'):
            enhanced_parts.append(f"[id='{attributes['id']}']")  
        if attributes.get('name'):
            enhanced_parts.append(f"[name='{attributes['name']}']")  
        if attributes.get('aria-label'):
            enhanced_parts.append(f"[aria-label*='{attributes['aria-label'][:30]}']")  
        if attributes.get('placeholder'):
            enhanced_parts.append(f"[placeholder='{attributes['placeholder']}']")  
        if attributes.get('type'):
            enhanced_parts.append(f"[type='{attributes['type']}']")  
        
        # Always include at least 2 element details if available
        if len(enhanced_parts) >= 2:
            return ''.join(enhanced_parts[:4])  # Use up to 4 attributes for specificity
        else:
            # Fallback to original CSS
            return css_selector
    
    @staticmethod
    def _generate_enhanced_xpath(element: Dict[str, Any], step: Dict[str, Any]) -> str:
        """
        Generate enhanced XPath selectors combining multiple attributes for resilience.
        
        Args:
            element: Element dictionary containing tag, id, className, text, etc.
            step: Step dictionary containing action, navigation, and locators
            
        Returns:
            Enhanced XPath string with multiple attribute conditions
        """
        # Extract element attributes
        tag_name = element.get('tagName', '').lower() or 'input'
        elem_id = element.get('id', '').strip()
        class_name = element.get('className', '').strip()
        text_content = element.get('textContent', '').strip()
        name_attr = element.get('name', '').strip()
        placeholder = element.get('placeholder', '').strip()
        
        # Build XPath conditions
        conditions = []
        
        # Add ID condition if available (most reliable)
        if elem_id:
            conditions.append(f"@id='{elem_id}'")
        
        # Add name attribute if available
        if name_attr:
            conditions.append(f"@name='{name_attr}'")
        
        # Add placeholder for input fields
        if placeholder and tag_name in ['input', 'textarea']:
            conditions.append(f"@placeholder='{placeholder}'")
        
        # Add class if available (less reliable, so combine with others)
        if class_name:
            # Use contains for classes to handle multiple class names
            conditions.append(f"contains(@class, '{class_name.split()[0]}')")
        
        # Add text content for buttons/links
        if text_content and tag_name in ['button', 'a', 'span', 'div']:
            conditions.append(f"text()='{text_content}'")
        
        # If we have multiple conditions, combine them
        if len(conditions) >= 2:
            xpath = f"//{tag_name}[{' and '.join(conditions)}]"
        elif len(conditions) == 1:
            xpath = f"//{tag_name}[{conditions[0]}]"
        else:
            # Fallback: use tag name only (least reliable)
            xpath = f"//{tag_name}"
        
        return xpath

    def _build_page_based_payload(
        self,
        scenario: str,
        framework: FrameworkProfile,
        vector_steps: List[Dict[str, Any]],
        keep_signatures: Optional[Set[str]] = None,
    ) -> Dict[str, List[Dict[str, str]]]:
        """
        Generate payload with page-based file organization.
        Groups steps by pageTitle and generates separate files per page.
        """
        # Group steps by page title
        grouped_pages = _group_steps_by_page_title(vector_steps)
        
        # Storage for data bindings across all pages
        all_data_bindings: List[Dict[str, Any]] = []
        
        # Get existing pages and login/home URLs for smart reuse
        existing_pages = _scan_existing_pages(framework)
        existing_locators = _scan_existing_locators(framework)
        login_home_urls = _get_login_home_urls(framework)
        
        # Storage for generated files
        all_locator_files = []
        all_page_files = []
        page_imports = []  # For test file
        
        root = framework.root
        def resolve_relative(target: Path) -> str:
            return str(target.relative_to(root)).replace('\\', '/')
        
        # Process each page
        for page_title, page_steps in grouped_pages.items():
            # Use page title directly for file names (not slugified)
            # Sanitize only characters that are invalid for file names
            page_file_name = page_title.replace('/', '-').replace('\\', '-').replace(':', '-').replace('*', '-').replace('?', '-').replace('"', '').replace('<', '-').replace('>', '-').replace('|', '-')
            page_class_name = f"{_to_camel_case(_slugify(page_title)).capitalize()}Page"
            
            # Get page URL for login/home detection
            page_url = ""
            for step in page_steps:
                page_url = step.get('pageUrl') or step.get('original_url') or page_url
                if page_url:
                    break
            
            # Check if this is login or home page
            is_login = 'login' in login_home_urls and _urls_match(page_url, login_home_urls['login'])
            is_home = 'home' in login_home_urls and _urls_match(page_url, login_home_urls['home'])
            
            if is_login or is_home:
                # Skip generation, use existing page
                existing_class = "LoginPage" if is_login else "HomePage"
                existing_file = f"login.page" if is_login else "home.page"
                page_imports.append({
                    'className': existing_class,
                    'fileName': existing_file,
                    'isExisting': True,
                    'pageTitle': page_title
                })
                logger.info(f"Reusing existing {existing_class} for page: {page_title}")
                continue
            
            # Generate locators and page files for this page using page title as file name
            locators_path = (framework.locators_dir or root / 'locators') / f"{page_file_name}.locators.ts"
            page_filename = f"{page_file_name}.page.ts"
            page_path = (framework.pages_dir or root / 'pages') / page_filename
            
            # Generate locators content
            locators_content, page_data_bindings = self._generate_locators_for_page(page_steps, page_file_name)
            
            # Collect data bindings
            all_data_bindings.extend(page_data_bindings)
            
            # Generate page class content
            page_content = self._generate_page_class_for_page(
                page_steps, page_class_name, locators_path, page_path, framework
            )
            
            # Add to collections
            all_locator_files.append({'path': resolve_relative(locators_path), 'content': locators_content})
            all_page_files.append({'path': resolve_relative(page_path), 'content': page_content})
            
            page_imports.append({
                'className': page_class_name,
                'fileName': page_file_name,  # Use actual page title for imports
                'isExisting': False,
                'pageTitle': page_title,
                'varName': page_class_name[0].lower() + page_class_name[1:] if page_class_name else 'page'
            })
        
        # Generate single test file that orchestrates all pages
        # Use flow_name from steps if available, otherwise slugify scenario
        flow_name = vector_steps[0].get('flow_name') if vector_steps else None
        test_slug = flow_name if flow_name else _slugify(scenario)
        test_path = (framework.tests_dir or root / 'tests') / f"{test_slug}.spec.ts"
        test_content = self._generate_multi_page_test(scenario, page_imports, grouped_pages, test_path, framework)
        
        # Build test data mapping from collected bindings
        test_data_mapping = []
        data_key_map = {}
        for binding in all_data_bindings:
            data_key = binding['data_key']
            if data_key not in data_key_map:
                data_key_map[data_key] = {
                    'columnName': data_key,
                    'occurrences': 0,
                    'actionType': binding['action_category'],
                    'methods': []
                }
            data_key_map[data_key]['occurrences'] += 1
            data_key_map[data_key]['methods'].append(binding['method_name'])
        
        test_data_mapping = list(data_key_map.values())
        
        # Debug: Log the paths being returned
        logger.info(f"Page-based payload: {len(all_locator_files)} locators, {len(all_page_files)} pages, 1 test")
        for loc_file in all_locator_files:
            logger.info(f"  Locator path: {loc_file['path']}")
        for page_file in all_page_files:
            logger.info(f"  Page path: {page_file['path']}")
        logger.info(f"  Test path: {resolve_relative(test_path)}")
        
        return {
            'locators': all_locator_files,
            'pages': all_page_files,
            'tests': [{'path': resolve_relative(test_path), 'content': test_content}],
            'testDataMapping': test_data_mapping
        }

    def _generate_locators_for_page(
        self, page_steps: List[Dict[str, Any]], page_slug: str
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """Generate locators file content for a single page and extract data bindings."""
        selector_to_key: Dict[str, str] = {}
        used_keys: set[str] = set()
        entries: List[Tuple[str, str]] = []
        data_bindings: List[Dict[str, Any]] = []
        method_names: set[str] = set()
        
        for index, step in enumerate(page_steps):
            element = step.get('element') or {}
            selector_obj = element.get('selector', {})
            visible_text = step.get('visibleText', '').strip()
            playwright_sel = selector_obj.get('playwright', {})
            
            # NEW PRIORITY: Visible text + Playwright > Visible text + CSS > Playwright + CSS/XPath > HTML + CSS > XPath + HTML
            selector = ''
            selector_source = ''
            
            # PRIORITY 1: Visible text + Playwright properties (BEST)
            if visible_text and playwright_sel and isinstance(playwright_sel, dict):
                pw_methods = []
                for pw_key, pw_value in playwright_sel.items():
                    if pw_value:
                        pw_methods.append(pw_value)
                if pw_methods:
                    # Combine visible text with Playwright selector
                    selector = f"{pw_methods[0]}"
                    selector_source = f"visible_text+playwright ({visible_text})"
                    logger.info(f"Step {index + 1}: Using visible text + Playwright: {selector}")
            
            # PRIORITY 2: Visible text + CSS (if Playwright not available)
            if not selector and visible_text:
                css_selector = selector_obj.get('css', '')
                if css_selector:
                    # Build composite selector with text validation
                    if css_selector.startswith('//'):
                        selector = f"xpath={css_selector}[contains(text(), '{visible_text}')]"
                    else:
                        selector = f"{css_selector}:has-text('{visible_text}')"
                    selector_source = f"visible_text+css ({visible_text})"
                    logger.info(f"Step {index + 1}: Using visible text + CSS: {selector}")
            
            # PRIORITY 3: Playwright properties + CSS/XPath (no visible text)
            if not selector and playwright_sel and isinstance(playwright_sel, dict):
                css_selector = selector_obj.get('css', '')
                xpath_selector = selector_obj.get('xpath', '')
                
                # Try Playwright + CSS first
                if css_selector:
                    pw_value = next((v for v in playwright_sel.values() if v), None)
                    if pw_value:
                        # Combine both for resilience
                        selector = f"{pw_value} >> {css_selector}"
                        selector_source = "playwright+css"
                        logger.info(f"Step {index + 1}: Using Playwright + CSS: {selector}")
                # Try Playwright + XPath if CSS not available
                elif xpath_selector:
                    pw_value = next((v for v in playwright_sel.values() if v), None)
                    if pw_value:
                        selector = f"{pw_value} >> xpath={xpath_selector}"
                        selector_source = "playwright+xpath"
                        logger.info(f"Step {index + 1}: Using Playwright + XPath: {selector}")
            
            # PRIORITY 4: HTML + CSS properties (both not available)
            if not selector:
                css_selector = selector_obj.get('css', '')
                element_html = element.get('html', '')
                if css_selector and element_html:
                    # Extract key attributes from HTML to enhance CSS
                    selector = self._generate_html_css_combo(css_selector, element_html, step)
                    selector_source = "html+css"
                    logger.info(f"Step {index + 1}: Using HTML + CSS combo: {selector}")
            
            # PRIORITY 5: XPath + HTML properties (last resort)
            if not selector:
                element_html = element.get('html', '')
                if element_html:
                    try:
                        selector = self._generate_enhanced_xpath(element, step)
                        selector = f"xpath={selector}" if not selector.startswith('xpath=') else selector
                        selector_source = "xpath+html (generated)"
                        logger.info(f"Step {index + 1}: Using enhanced XPath: {selector}")
                    except Exception as e:
                        logger.warning(f"Failed to generate enhanced XPath: {e}")
            
            if not selector:
                logger.warning(f"No selector found for step {index + 1}, skipping")
                continue
            
            # Skip duplicates
            if selector in selector_to_key:
                continue
            
            # Generate key name from navigation or action
            navigation = step.get('navigation', '')
            action = step.get('action', '')
            base_name = navigation or action or f'step{index + 1}'
            base_key = _to_camel_case(base_name) or f'step{index + 1}'
            key = base_key
            suffix = 2
            while key in used_keys:
                key = f"{base_key}{suffix}"
                suffix += 1
            
            selector_to_key[selector] = key
            used_keys.add(key)
            entries.append((key, selector))
            
            # Extract data bindings for input/select fields
            action_lower = action.lower()
            if action_lower in ['input', 'fill', 'type', 'select']:
                data_key = _extract_data_key(step)
                if not data_key:
                    # Extract from navigation
                    data_key = navigation.replace('Enter', '').replace('Select', '').replace('Choose', '').strip()
                
                if data_key:
                    action_category = 'select' if action_lower == 'select' else 'fill'
                    
                    method_suffix = _to_camel_case(data_key)
                    if method_suffix:
                        method_suffix = method_suffix[:1].upper() + method_suffix[1:]
                    else:
                        method_suffix = key.title()
                    
                    # Use method_suffix as the actual column name (what code expects)
                    actual_column_name = method_suffix
                    
                    prefix = 'set' if action_category != 'select' else 'select'
                    candidate_name = prefix + method_suffix
                    if candidate_name in method_names:
                        counter = 2
                        base_candidate = candidate_name
                        while candidate_name in method_names:
                            candidate_name = f"{base_candidate}{counter}"
                            counter += 1
                    method_names.add(candidate_name)
                    
                    normalised_key = re.sub(r'[^a-z0-9]+', '', actual_column_name.lower())
                    data_bindings.append({
                        'locator_key': key,
                        'data_key': actual_column_name,
                        'normalised': normalised_key,
                        'method_name': candidate_name,
                        'fallback': _extract_data_value(step),
                        'action_category': action_category,
                    })
        
        # Generate locators file
        locators_lines = ['const locators = {'] + [
            f"  {key}: {json.dumps(selector)}," for key, selector in entries
        ] + ['};', '', 'export default locators;']
        
        return "\n".join(locators_lines) + os.linesep, data_bindings
    
    def _generate_page_class_for_page(
        self,
        page_steps: List[Dict[str, Any]],
        page_class_name: str,
        locators_path: Path,
        page_path: Path,
        framework: FrameworkProfile
    ) -> str:
        """Generate page class file content for a single page with full structure."""
        
        # Extract locator keys and data bindings
        locator_keys = []
        data_bindings = []
        used_keys = set()
        method_names = set()
        
        for index, step in enumerate(page_steps):
            # Generate locator key name
            navigation = step.get('navigation', '')
            action = step.get('action', '')
            base_name = navigation or action or f'step{index + 1}'
            base_key = _to_camel_case(base_name) or f'step{index + 1}'
            key = base_key
            suffix = 2
            while key in used_keys:
                key = f"{base_key}{suffix}"
                suffix += 1
            used_keys.add(key)
            locator_keys.append(key)
            
            # Extract data bindings
            action_lower = action.lower()
            if action_lower in ['input', 'fill', 'type', 'select']:
                data_key = _extract_data_key(step)
                if not data_key:
                    data_key = navigation.replace('Enter', '').replace('Select', '').replace('Choose', '').strip()
                
                if data_key:
                    action_category = 'select' if action_lower == 'select' else 'fill'
                    method_suffix = _to_camel_case(data_key)
                    if method_suffix:
                        method_suffix = method_suffix[:1].upper() + method_suffix[1:]
                    else:
                        method_suffix = key.title()
                    
                    # Use method_suffix as the actual column name (what code expects)
                    actual_column_name = method_suffix
                    
                    prefix = 'set' if action_category != 'select' else 'select'
                    candidate_name = prefix + method_suffix
                    if candidate_name in method_names:
                        counter = 2
                        base_candidate = candidate_name
                        while candidate_name in method_names:
                            candidate_name = f"{base_candidate}{counter}"
                            counter += 1
                    method_names.add(candidate_name)
                    
                    data_bindings.append({
                        'locator_key': key,
                        'data_key': actual_column_name,
                        'method_name': candidate_name,
                        'action_category': action_category,
                    })
        
        # Start building page class
        page_lines = [
            "import { Page, Locator } from '@playwright/test';",
            'import HelperClass from "../util/methods.utility.ts";',
            f'import locators from "{_relative_import(page_path, locators_path)}";',
            '',
            f'class {page_class_name} {{',
            '  page: Page;',
            '  helper: HelperClass;',
        ]
        
        # Add locator properties
        for key in locator_keys:
            page_lines.append(f'  {key}: Locator;')
        
        page_lines.extend([
            '',
            '  constructor(page: Page) {',
            '    this.page = page;',
            '    this.helper = new HelperClass(page);',
        ])
        
        # Initialize locators in constructor
        for key in locator_keys:
            page_lines.append(f'    this.{key} = page.locator(locators.{key});')
        
        page_lines.extend([
            '  }',
            '',
            '  private coerceValue(value: unknown): string {',
            '    if (value === undefined || value === null) {',
            "      return '';",
            '    }',
            '    if (typeof value === \'number\') {',
            '      return `${value}`;',
            '    }',
            '    if (typeof value === \'string\') {',
            '      return value;',
            '    }',
            "    return `${value ?? ''}`;",
            '  }',
            '',
            '  private normaliseDataKey(value: string): string {',
            "    return (value || '').replace(/[^a-z0-9]+/gi, '').toLowerCase();",
            '  }',
            '',
            "  private resolveDataValue(formData: Record<string, any> | null | undefined, key: string, fallback: string = ''): string {",
            '    const target = this.normaliseDataKey(key);',
            '    if (formData) {',
            '      for (const entryKey of Object.keys(formData)) {',
            '        if (this.normaliseDataKey(entryKey) === target) {',
            '          const candidate = this.coerceValue(formData[entryKey]);',
            "          if (candidate.trim() !== '') {",
            '            return candidate;',
            '          }',
            '        }',
            '      }',
            '    }',
            '    return this.coerceValue(fallback);',
            '  }',
        ])
        
        # Add setter methods for data bindings
        for binding in data_bindings:
            method_name = binding['method_name']
            locator_key = binding['locator_key']
            action_category = binding['action_category']
            
            page_lines.extend([
                '',
                '  async ' + method_name + '(value: unknown): Promise<void> {',
                '    const finalValue = this.coerceValue(value);',
                f'    await this.{locator_key}.fill(finalValue);',
                '  }',
            ])
        
        # Add applyData method if there are data bindings
        if data_bindings:
            page_lines.extend([
                '',
                '  async applyData(formData: Record<string, any> | null | undefined, keys?: string[], index: number = 0): Promise<void> {',
                '    const fallbackValues: Record<string, string> = {',
            ])
            
            for binding in data_bindings:
                data_key = binding['data_key']
                page_lines.append(f'      "{data_key}": "",')
            
            page_lines.extend([
                '    };',
                '    const targetKeys = Array.isArray(keys) && keys.length ? keys.map((key) => this.normaliseDataKey(key)) : null;',
                '    const shouldHandle = (key: string) => {',
                '      if (!targetKeys) {',
                '        return true;',
                '      }',
                '      return targetKeys.includes(this.normaliseDataKey(key));',
                '    };',
            ])
            
            for binding in data_bindings:
                data_key = binding['data_key']
                method_name = binding['method_name']
                page_lines.extend([
                    f'    if (shouldHandle("{data_key}")) {{',
                    f'      await this.{method_name}(this.resolveDataValue(formData, "{data_key}", fallbackValues["{data_key}"] ?? \'\'));',
                    '    }',
                ])
            
            page_lines.append('  }')
        
        page_lines.extend([
            '}',
            '',
            f'export default {page_class_name};'
        ])
        
        return "\n".join(page_lines) + os.linesep
    
    def _generate_multi_page_test(
        self,
        scenario: str,
        page_imports: List[Dict[str, Any]],
        grouped_pages: Dict[str, List[Dict[str, Any]]],
        test_path: Path,
        framework: FrameworkProfile
    ) -> str:
        """Generate test file that orchestrates multiple pages."""
        scenario_literal = json.dumps(scenario)
        
        spec_lines = [
            'import { test } from "../testSetup";',
        ]
        
        # Add imports for all pages
        for page_info in page_imports:
            class_name = page_info['className']
            file_name = page_info['fileName']
            if page_info['isExisting']:
                # Import from pages directory
                spec_lines.append(f'import {class_name} from "../pages/{file_name}";')
            else:
                # Import generated page
                page_path = framework.pages_dir / f"{class_name}.ts"
                rel_import = _relative_import(test_path, page_path)
                spec_lines.append(f'import {class_name} from "{rel_import}";')
        
        spec_lines.extend([
            '',
            f'test.describe({scenario_literal}, () => {{',
        ])
        
        # Declare page object variables
        for page_info in page_imports:
            class_name = page_info['className']
            var_name = page_info.get('varName', class_name[:1].lower() + class_name[1:])
            spec_lines.append(f'  let {var_name}: {class_name};')
        
        spec_lines.extend([
            '',
            f'  test({scenario_literal}, async ({{ page }}) => {{',
        ])
        
        # Extract start URL from first page's first step
        start_url = ''
        if grouped_pages:
            first_page_steps = next(iter(grouped_pages.values()))
            if first_page_steps:
                start_url = first_page_steps[0].get('pageUrl') or first_page_steps[0].get('original_url') or ''
        
        # Add navigation to start URL
        if start_url:
            spec_lines.append(f'    await page.goto({json.dumps(start_url)});')
            spec_lines.append('')
        
        # Initialize page objects
        for page_info in page_imports:
            class_name = page_info['className']
            var_name = page_info.get('varName', class_name[:1].lower() + class_name[1:])
            spec_lines.append(f'    {var_name} = new {class_name}(page);')
        
        spec_lines.append('')
        
        # Generate test steps for each page
        for page_info in page_imports:
            page_title = page_info['pageTitle']
            var_name = page_info.get('varName')
            page_steps = grouped_pages.get(page_title, [])
            
            if not page_steps:
                continue
            
            spec_lines.append(f'    // {page_title} steps')
            
            for step in page_steps:
                action = step.get('action', '').lower()
                element_name = step.get('element_name') or step.get('element_type') or 'element'
                
                # Generate method call based on action
                if action in ['click', 'click button', 'button_click']:
                    spec_lines.append(f'    await {var_name}.click{_to_camel_case(element_name).capitalize()}();')
                elif action in ['fill', 'fill text', 'input', 'type']:
                    spec_lines.append(f'    await {var_name}.fill{_to_camel_case(element_name).capitalize()}("value");  // TODO: Replace with actual value')
                elif action in ['select', 'dropdown']:
                    spec_lines.append(f'    await {var_name}.select{_to_camel_case(element_name).capitalize()}("option");  // TODO: Replace with actual option')
                elif action in ['check', 'checkbox']:
                    spec_lines.append(f'    await {var_name}.check{_to_camel_case(element_name).capitalize()}();')
                elif action in ['navigate', 'goto']:
                    page_url = step.get('pageUrl') or step.get('original_url') or ''
                    if page_url and page_url != start_url:
                        spec_lines.append(f'    await page.goto({json.dumps(page_url)});')
                else:
                    # Generic action comment
                    spec_lines.append(f'    // TODO: {action} on {element_name}')
            
            spec_lines.append('')
        
        spec_lines.extend([
            '  });',
            '});'
        ])
        
        return "\n".join(spec_lines) + os.linesep

    def _build_deterministic_payload(
        self,
        scenario: str,
        framework: FrameworkProfile,
        vector_steps: List[Dict[str, Any]],
        keep_signatures: Optional[Set[str]] = None,
    ) -> Dict[str, List[Dict[str, str]]]:
        # Check if steps have pageTitle enrichment for page-based generation
        page_titles = set()
        for step in vector_steps:
            page_title = step.get('pageTitle') or step.get('page_title')
            if page_title and page_title != 'Unknown':
                page_titles.add(page_title)
        
        logger.info(f"[Page Detection] Found {len(page_titles)} unique pages: {sorted(page_titles)}")
        logger.info(f"[Page Detection] First step data: {vector_steps[0] if vector_steps else 'No steps'}")
        
        if len(page_titles) >= 2:  # Use page-based generation only if we have 2+ distinct pages
            logger.info(f"Page-based generation: {len(page_titles)} unique pages detected")
            logger.info(f"Pages: {sorted(page_titles)}")
            return self._build_page_based_payload(scenario, framework, vector_steps, keep_signatures)
        else:
            logger.info(f"Single-file generation: Only {len(page_titles)} unique page(s) detected, using single-file approach")
        
        # Single page or no page info - use original single-file generation
        slug = _slugify(scenario)
        root = framework.root

        def resolve_relative(target: Path) -> str:
            return str(target.relative_to(root)).replace('\\', '/')

        if framework.locators_dir:
            locators_path = framework.locators_dir / f"{slug}.ts"
        else:
            locators_path = root / 'locators' / f"{slug}.ts"
        if framework.pages_dir:
            page_filename = f"{_to_camel_case(slug).capitalize() or 'Generated'}Page.ts"
            page_path = framework.pages_dir / page_filename
        else:
            page_path = root / 'pages' / f"{_to_camel_case(slug).capitalize() or 'Generated'}Page.ts"
        if framework.tests_dir:
            test_path = framework.tests_dir / f"{slug}.spec.ts"
        else:
            test_path = root / 'tests' / f"{slug}.spec.ts"

        search_dirs: List[Path] = []
        if framework.pages_dir and framework.pages_dir.exists():
            search_dirs.append(framework.pages_dir)
        else:
            fallback_pages_dir = root / 'pages'
            if fallback_pages_dir.exists():
                search_dirs.append(fallback_pages_dir)

        login_page_file: Optional[Path] = None
        home_page_file: Optional[Path] = None

        for directory in search_dirs:
            matches = list(directory.glob('**/login.page.ts'))
            if matches:
                login_page_file = matches[0]
                break

        for directory in search_dirs:
            matches = list(directory.glob('**/home.page.ts'))
            if matches:
                home_page_file = matches[0]
                break

        login_key_candidates = {
            "username",
            "userid",
            "user",
            "signin",
            "sign_in",
            "password",
            "enterpasscode",
            "passcode",
            "verify",
        }

        selector_to_key: Dict[str, str] = {}
        used_keys: set[str] = set()
        entries: List[Tuple[str, str]] = []
        entry_keys: set[str] = set()
        step_refs: List[Dict[str, Any]] = []
        data_bindings: List[Dict[str, Any]] = []
        method_names: set[str] = set()

        if keep_signatures is not None and len(keep_signatures) < 2:
            keep_signatures = None

        effective_steps: List[Dict[str, Any]]
        if keep_signatures:
            filtered_steps = [
                step for step in vector_steps if _step_signature(step) in keep_signatures
            ]
            effective_steps = filtered_steps or vector_steps
            # Debug: show what was filtered
            print(f"[DEBUG] Filtered {len(vector_steps)} -> {len(effective_steps)} steps based on preview signatures")
        else:
            effective_steps = vector_steps

        for index, step in enumerate(effective_steps):
            locators = step.get('locators') or {}
            signature = _step_signature(step)
            if keep_signatures is not None and signature not in keep_signatures:
                continue
            # Priority: 1) playwright 2) css 3) xpath
            selector = _normalize_selector(
                locators.get('playwright')
                or locators.get('css')
                or locators.get('stable')
                or locators.get('xpath')
                or locators.get('raw_xpath')
                or locators.get('selector')
                or ''
            )
            if not selector:
                element = step.get('element') or {}
                selector = _normalize_selector(
                    element.get('playwright')
                    or element.get('css')
                    or element.get('stable')
                    or element.get('xpath')
                    or element.get('raw_xpath')
                )
            if not selector:
                raise ValueError(
                    f"No selector resolved for step {index + 1} "
                    f"(action={step.get('action')!r}, navigation={step.get('navigation')!r}). "
                    'Ensure the refined recorder flow includes CSS or stable selectors.'
                )

            if selector in selector_to_key:
                key = selector_to_key[selector]
            else:
                base_name = (
                    locators.get('name')
                    or locators.get('title')
                    or locators.get('labels')
                    or step.get('navigation')
                    or step.get('action')
                    or f'step{index + 1}'
                )
                base_key = _to_camel_case(base_name) or f'step{index + 1}'
                key = base_key
                suffix = 2
                while key in used_keys:
                    key = f"{base_key}{suffix}"
                    suffix += 1
                selector_to_key[selector] = key
                used_keys.add(key)

            navigation = step.get('navigation') or ''
            nav_lower = navigation.lower()
            handled_by: Optional[str] = None
            key_lower = key.lower()

            if login_page_file:
                login_keywords = [
                    'user name',
                    'username',
                    'password',
                    'sign in',
                    'signin',
                    'passcode',
                    'verify',
                    'login page',
                ]
                if any(term in nav_lower for term in login_keywords) or any(candidate in key_lower for candidate in login_key_candidates):
                    handled_by = 'login'

            if not handled_by and key not in entry_keys:
                entries.append((key, selector))
                entry_keys.add(key)

            step_ref: Dict[str, Any] = {
                'key': key,
                'action': (step.get('action') or '').lower(),
                'data': _extract_data_value(step),
                'raw': step,
            }
            if handled_by:
                step_ref['handled_by'] = handled_by
            step_refs.append(step_ref)

            data_key = _extract_data_key(step)
            if data_key and not handled_by:
                action_lower = (step.get('action') or '').lower()
                action_category = 'fill'
                if 'select' in action_lower or 'dropdown' in nav_lower or 'choose' in nav_lower:
                    action_category = 'select'
                method_suffix = _to_camel_case(data_key) or _to_camel_case(navigation) or key
                if method_suffix:
                    method_suffix = method_suffix[:1].upper() + method_suffix[1:]
                else:
                    method_suffix = key.title()
                
                # Use method_suffix as the actual column name (what code expects)
                actual_column_name = method_suffix
                
                prefix = 'set' if action_category != 'select' else 'select'
                candidate_name = prefix + (method_suffix[:1].upper() + method_suffix[1:])
                if candidate_name in method_names:
                    counter = 2
                    base_candidate = candidate_name
                    while candidate_name in method_names:
                        candidate_name = f"{base_candidate}{counter}"
                        counter += 1
                method_names.add(candidate_name)
                normalised_key = re.sub(r'[^a-z0-9]+', '', actual_column_name.lower())
                data_bindings.append(
                    {
                        'locator_key': key,
                        'data_key': actual_column_name,
                        'normalised': normalised_key,
                        'method_name': candidate_name,
                        'fallback': _extract_data_value(step),
                        'action_category': action_category,
                    }
                )
                step_ref['data_key'] = data_key
                step_ref['method_name'] = candidate_name
                step_ref['action_category'] = action_category

        locators_lines = ['const locators = {'] + [
            f"  {key}: {json.dumps(selector)}," for key, selector in entries
        ] + ['};', '', 'export default locators;']
        locators_content = "\n".join(locators_lines) + os.linesep

        page_class = _to_camel_case(Path(page_path).stem).capitalize() or 'GeneratedPage'
        page_var = page_class[:1].lower() + page_class[1:] if page_class else 'pageObject'
        page_lines: List[str] = [
            "import { Page, Locator } from '@playwright/test';",
            f'import locators from "{_relative_import(page_path, locators_path)}";',
        ]

        helper_candidates = [
            root / 'util' / 'methods.utility.ts',
            root / 'util' / 'methods.utility',
            root / 'utils' / 'methods.utility.ts',
            root / 'utils' / 'methods.utility',
        ]
        helper_path = next((candidate for candidate in helper_candidates if candidate.exists()), None)
        helper_available = helper_path is not None
        if helper_available:
            page_lines.insert(
                1,
                f'import HelperClass from "{_relative_import(page_path, helper_path)}";',
            )
        for binding in data_bindings:
            binding['use_helper'] = helper_available and binding['action_category'] == 'select'

        page_lines.append('')
        page_lines.append(f'class {page_class} {{')
        page_lines.append('  page: Page;')
        if helper_available:
            page_lines.append('  helper: HelperClass;')
        for key, _ in entries:
            page_lines.append(f'  {key}: Locator;')
        page_lines.append('')
        page_lines.append('  constructor(page: Page) {')
        page_lines.append('    this.page = page;')
        if helper_available:
            page_lines.append('    this.helper = new HelperClass(page);')
        for key, _ in entries:
            page_lines.append(f'    this.{key} = page.locator(locators.{key});')
        page_lines.append('  }')

        if data_bindings:
            page_lines.append('')
            page_lines.append("  private coerceValue(value: unknown): string {")
            page_lines.append("    if (value === undefined || value === null) {")
            page_lines.append("      return '';")
            page_lines.append('    }')
            page_lines.append("    if (typeof value === 'number') {")
            page_lines.append("      return `${value}`;")
            page_lines.append('    }')
            page_lines.append("    if (typeof value === 'string') {")
            page_lines.append('      return value;')
            page_lines.append('    }')
            page_lines.append("    return `${value ?? ''}`;")
            page_lines.append('  }')
            page_lines.append('')
            page_lines.append("  private normaliseDataKey(value: string): string {")
            page_lines.append("    return (value || '').replace(/[^a-z0-9]+/gi, '').toLowerCase();")
            page_lines.append('  }')
            page_lines.append('')
            page_lines.append("  private resolveDataValue(formData: Record<string, any> | null | undefined, key: string, fallback: string = ''): string {")
            page_lines.append('    const target = this.normaliseDataKey(key);')
            page_lines.append('    if (formData) {')
            page_lines.append('      for (const entryKey of Object.keys(formData)) {')
            page_lines.append('        if (this.normaliseDataKey(entryKey) === target) {')
            page_lines.append('          const candidate = this.coerceValue(formData[entryKey]);')
            page_lines.append("          if (candidate.trim() !== '') {")
            page_lines.append('            return candidate;')
            page_lines.append('          }')
            page_lines.append('        }')
            page_lines.append('      }')
            page_lines.append('    }')
            page_lines.append('    return this.coerceValue(fallback);')
            page_lines.append('  }')

        fallback_map: Dict[str, str] = {}
        for binding in data_bindings:
            fallback_map[binding['data_key']] = ""

        for binding in data_bindings:
            method_name = binding['method_name']
            locator_key = binding['locator_key']
            action_category = binding['action_category']
            use_helper = binding['use_helper']
            page_lines.append('')
            page_lines.append(f'  async {method_name}(value: unknown): Promise<void> {{')
            page_lines.append('    const finalValue = this.coerceValue(value);')
            if action_category == 'select' and use_helper:
                page_lines.append(f'    await this.helper.compoundElementSelection(this.{locator_key}, finalValue);')
            elif action_category == 'select':
                page_lines.append(f'    await this.{locator_key}.selectOption(finalValue);')
            else:
                page_lines.append(f'    await this.{locator_key}.fill(finalValue);')
            page_lines.append('  }')

        if data_bindings:
            # Track occurrences of each data key
            from collections import defaultdict
            key_occurrences: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
            for binding in data_bindings:
                key_occurrences[binding['data_key']].append(binding)
            
            page_lines.append('')
            page_lines.append('  async applyData(formData: Record<string, any> | null | undefined, keys?: string[], index: number = 0): Promise<void> {')
            page_lines.append('    const fallbackValues: Record<string, string> = {')
            for data_key, fallback in fallback_map.items():
                page_lines.append(f"      {json.dumps(data_key)}: {json.dumps(fallback or '')},")
            page_lines.append('    };')
            page_lines.append('    const targetKeys = Array.isArray(keys) && keys.length ? keys.map((key) => this.normaliseDataKey(key)) : null;')
            page_lines.append('    const shouldHandle = (key: string) => {')
            page_lines.append('      if (!targetKeys) {')
            page_lines.append('        return true;')
            page_lines.append('      }')
            page_lines.append('      return targetKeys.includes(this.normaliseDataKey(key));')
            page_lines.append('    };')
            
            # Generate if blocks with index tracking for duplicate keys
            for data_key, bindings_list in key_occurrences.items():
                if len(bindings_list) == 1:
                    # Single occurrence - no index needed
                    binding = bindings_list[0]
                    method_name = binding['method_name']
                    page_lines.append(f"    if (shouldHandle({json.dumps(data_key)})) {{")
                    page_lines.append(f"      await this.{method_name}(this.resolveDataValue(formData, {json.dumps(data_key)}, fallbackValues[{json.dumps(data_key)}] ?? ''));")
                    page_lines.append('    }')
                else:
                    # Multiple occurrences - use index to select which one
                    page_lines.append(f"    if (shouldHandle({json.dumps(data_key)})) {{")
                    page_lines.append(f"      const value = this.resolveDataValue(formData, {json.dumps(data_key)}, fallbackValues[{json.dumps(data_key)}] ?? '');")
                    for idx, binding in enumerate(bindings_list):
                        method_name = binding['method_name']
                        if idx == 0:
                            page_lines.append(f"      if (index === {idx}) {{")
                        else:
                            page_lines.append(f"      }} else if (index === {idx}) {{")
                        page_lines.append(f"        await this.{method_name}(value);")
                    page_lines.append('      }')  # Close the if-else chain
                    page_lines.append('    }')  # Close the shouldHandle if
            page_lines.append('  }')

        page_lines.append('}')
        page_lines.append('')
        page_lines.append(f'export default {page_class};')
        page_content = "\n".join(page_lines) + os.linesep

        scenario_literal = json.dumps(scenario)
        spec_lines = [
            'import { test } from "../testSetup";',
            f'import PageObject from "{_relative_import(test_path, page_path)}";',
        ]
        if login_page_file:
            spec_lines.append(f'import LoginPage from "{_relative_import(test_path, login_page_file)}";')
        if home_page_file:
            spec_lines.append(f'import HomePage from "{_relative_import(test_path, home_page_file)}";')

        spec_lines.extend([
            'import { getTestToRun, shouldRun, readExcelData } from "../util/csvFileManipulation.ts";',
            'import { attachScreenshot, namedStep } from "../util/screenshot.ts";',
            "import * as dotenv from 'dotenv';",
            '',
            "const path = require('path');",
            "const fs = require('fs');",
            '',
            'dotenv.config();',
            'let executionList: any[];',
            '',
            'test.beforeAll(() => {',
            '  try {',
            "    const testManagerPath = path.join(__dirname, '../testmanager.xlsx');",
            '    if (fs.existsSync(testManagerPath)) {',
            "      executionList = getTestToRun(testManagerPath);",
            '    } else {',
            "      console.log('[TEST MANAGER] testmanager.xlsx not found - all tests will run');",
            '      executionList = [];',
            '    }',
            '  } catch (error) {',
            "    console.warn('[TEST MANAGER] Failed to load testmanager.xlsx - all tests will run. Error:', error.message);",
            '    executionList = [];',
            '  }',
            '});',
            '',
            f'test.describe({scenario_literal}, () => {{',
            f'  let {page_var}: PageObject;',
        ])

        if login_page_file:
            spec_lines.append('  let loginPage: LoginPage;')
        if home_page_file:
            spec_lines.append('  let homePage: HomePage;')
        spec_lines.append('')
        spec_lines.append('  const run = (name: string, fn: ({ page }, testinfo: any) => Promise<void>) =>')
        spec_lines.append('    (shouldRun(name) ? test : test.skip)(name, fn);')
        spec_lines.append('')
        spec_lines.append(f'  run({scenario_literal}, async ({{ page }}, testinfo) => {{')
        spec_lines.append(f'    {page_var} = new PageObject(page);')
        if login_page_file:
            spec_lines.append('    loginPage = new LoginPage(page);')
        if home_page_file:
            spec_lines.append('    homePage = new HomePage(page);')
        spec_lines.extend([
            '    const testCaseId = testinfo.title;',
            "    const testRow: Record<string, any> = executionList?.find((row: any) => row['TestCaseID'] === testCaseId) ?? {};",
            "    // Only use defaults if DatasheetName is explicitly provided (not empty)",
            "    const datasheetFromExcel = String(testRow?.['DatasheetName'] ?? '').trim();",
            "    const dataSheetName = datasheetFromExcel || '';",
            "    const envReferenceId = (process.env.REFERENCE_ID || process.env.DATA_REFERENCE_ID || '').trim();",
            "    const excelReferenceId = String(testRow?.['ReferenceID'] ?? '').trim();",
            "    const dataReferenceId = envReferenceId || excelReferenceId;",
            "    if (dataReferenceId) {",
            "      console.log(`[ReferenceID] Using: ${dataReferenceId} (source: ${envReferenceId ? 'env' : 'excel'})`);",
            "    }",
            "    const dataIdColumn = String(testRow?.['IDName'] ?? '').trim();",
            "    const dataSheetTab = String(testRow?.['SheetName'] ?? testRow?.['Sheet'] ?? '').trim();",
            "    const dataDir = path.join(__dirname, '../data');",
            '    fs.mkdirSync(dataDir, { recursive: true });',
            '    let dataRow: Record<string, any> = {};',
            '    const ensureDataFile = (): string | null => {',
            '      if (!dataSheetName) {',
            "        // No datasheet configured - skip data loading (optional datasheet)",
            '        return null;',
            '      }',
            '      const expectedPath = path.join(dataDir, dataSheetName);',
            '      if (!fs.existsSync(expectedPath)) {',
            '        const caseInsensitiveMatch = (() => {',
            '          try {',
            '            const entries = fs.readdirSync(dataDir, { withFileTypes: false });',
            '            const target = dataSheetName.toLowerCase();',
            '            const found = entries.find((entry) => entry.toLowerCase() === target);',
            '            return found ? path.join(dataDir, found) : null;',
            '          } catch (err) {',
            "            console.warn(`[DATA] Unable to scan data directory for ${dataSheetName}:`, err);",
            '            return null;',
            '          }',
            '        })();',
            '        if (caseInsensitiveMatch) {',
            '          return caseInsensitiveMatch;',
            '        }',
            "        const message = `Test data file '${dataSheetName}' not found in data/. Upload the file before running '${testCaseId}'.`;",
            "        console.warn(`[DATA] ${message}`);",
            '        throw new Error(message);',
            '      }',
            '      return expectedPath;',
            '    };',
            "    const normaliseKey = (value: string) => value.replace(/[^a-z0-9]/gi, '').toLowerCase();",
            '    const findMatchingDataKey = (sourceKey: string) => {',
            '      if (!sourceKey || !dataRow) {',
            '        return undefined;',
            '      }',
            '      const normalisedSource = normaliseKey(sourceKey);',
            '      return Object.keys(dataRow || {}).find((candidate) => normaliseKey(String(candidate)) === normalisedSource);',
            '    };',
            '    const getDataValue = (sourceKey: string, fallback: string) => {',
            '      if (!sourceKey) {',
            '        return fallback;',
            '      }',
            "      const directKey = findMatchingDataKey(sourceKey) || findMatchingDataKey(sourceKey.replace(/([A-Z])/g, '_$1'));",
            '      if (directKey) {',
            '        const candidate = dataRow?.[directKey];',
            "        if (candidate !== undefined && candidate !== null && `${candidate}`.trim() !== '') {",
            '          return `${candidate}`;',
            '        }',
            '      }',
            '      return fallback;',
            '    };',
            '    const dataPath = ensureDataFile();',
            '    if (dataPath && dataReferenceId && dataIdColumn) {',
            "      dataRow = readExcelData(dataPath, dataSheetTab || '', dataReferenceId, dataIdColumn) ?? {};",
            '      if (!dataRow || Object.keys(dataRow).length === 0) {',
            "        console.warn(`[DATA] Row not found in ${dataSheetName} for ${dataIdColumn}='${dataReferenceId}'.`);",
            '      }',
            '    } else if (!dataSheetName) {',
            "      console.log(`[DATA] No DatasheetName configured for ${testCaseId}. Test will run with hardcoded/default values.`);",
            '    } else if (dataSheetName && (!dataReferenceId || !dataIdColumn)) {',
            "      const missingFields = [];",
            "      if (!dataReferenceId) missingFields.push('ReferenceID');",
            "      if (!dataIdColumn) missingFields.push('IDName');",
            "      const message = `DatasheetName='${dataSheetName}' is provided but ${missingFields.join(' and ')} ${missingFields.length > 1 ? 'are' : 'is'} missing. Please provide ${missingFields.join(' and ')} in testmanager.xlsx for '${testCaseId}'.`;",
            "      console.error(`[DATA] ${message}`);",
            '      throw new Error(message);',
            '    }',
            '',
        ])

        login_step_emitted = False
        has_data_bindings = bool(data_bindings)
        test_step_counter = 0  # Separate counter for actual test steps (excludes login)
        
        # Extract original_url from first step (all steps should have the same original_url)
        original_url = ""
        first_non_login_selector = ""
        for ref in step_refs:
            raw = ref.get('raw') or {}
            original_url = raw.get('original_url') or original_url
            # Find first non-login step selector for waitForSelector
            if ref.get('handled_by') != 'login' and not first_non_login_selector:
                # Get selector from step_refs entry
                key = ref.get('key')
                if key:
                    # We'll use this key to generate the wait statement later
                    first_non_login_selector = key
        
        # Always emit navigation step as Step 0 if original_url is present
        if original_url:
            note = 'Navigate to application'
            step_title = json.dumps(f'Step {test_step_counter} - {note}')
            spec_lines.append(f'    await namedStep({step_title}, page, testinfo, async () => {{')
            spec_lines.append('      // Navigate to the application URL')
            spec_lines.append(f'      await page.goto({json.dumps(original_url)});')
            spec_lines.append('      const screenshot = await page.screenshot();')
            spec_lines.append(f'      attachScreenshot({step_title}, testinfo, screenshot);')
            spec_lines.append('    });')
            spec_lines.append('')
            test_step_counter += 1

        for idx, ref in enumerate(step_refs):
            raw = ref.get('raw') or {}
            handled_by = ref.get('handled_by')
            home_method = ref.get('home_method')

            # Skip any login steps (should already be filtered, but just in case)
            if handled_by == 'login':
                continue

            # Generate actual test step with correct sequential numbering
            note = raw.get('navigation') or raw.get('action') or raw.get('expected') or f'Step {test_step_counter}'
            step_title = json.dumps(f'Step {test_step_counter} - {note}')
            comment = raw.get('navigation') or raw.get('action') or ''
            key = ref.get('key')
            action = ref.get('action') or ''
            data_value = ref.get('data') or ''
            locator_expr = f"{page_var}.{key}" if key else ''

            spec_lines.append(f'    await namedStep({step_title}, page, testinfo, async () => {{')
            if comment:
                spec_lines.append(f'      // {comment}')
            fallback_literal = json.dumps(data_value or '')
            data_expr = fallback_literal
            if key:
                data_expr = f"getDataValue({json.dumps(key)}, {fallback_literal})"

            if has_data_bindings and ref.get('data_key'):
                keys_literal = json.dumps([ref['data_key']])
                # Track which occurrence of this data key we're at
                data_key = ref['data_key']
                occurrence_index = sum(1 for prev_ref in step_refs[:idx] if prev_ref.get('data_key') == data_key)
                spec_lines.append(f'      await {page_var}.applyData(dataRow, {keys_literal}, {occurrence_index});')
            elif key and any(token in action for token in ['fill', 'type', 'enter']):
                spec_lines.append(f'      await {locator_expr}.fill({data_expr});')
            elif key and 'select' in action:
                spec_lines.append(f'      await {locator_expr}.selectOption({data_expr});')
            elif key and 'press' in action:
                press_value = json.dumps(data_value or 'Enter')
                spec_lines.append(f'      await {locator_expr}.press({press_value});')
            elif 'goto' in action or 'navigate' in action:
                spec_lines.append(f'      await page.goto({data_expr});')
            elif key:
                spec_lines.append(f'      await {locator_expr}.click();')
            else:
                spec_lines.append('      // TODO: No selector provided by refined flow.')
            if raw.get('expected'):
                spec_lines.append(f"      // Expected: {raw['expected']}")
            spec_lines.append('      const screenshot = await page.screenshot();')
            spec_lines.append(f'      attachScreenshot({step_title}, testinfo, screenshot);')
            spec_lines.append('    });')
            spec_lines.append('')
            test_step_counter += 1  # Increment counter for each actual test step
        spec_lines.append('  });')
        spec_lines.append('});')
        spec_content = "\n".join(spec_lines).rstrip() + os.linesep

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
            'locators': [
                {'path': resolve_relative(locators_path), 'content': locators_content}
            ],
            'pages': [
                {'path': resolve_relative(page_path), 'content': page_content}
            ],
            'tests': [
                {'path': resolve_relative(test_path), 'content': spec_content}
            ],
            'testDataMapping': test_data_mapping,
        }

    @staticmethod
    def persist_payload(framework: FrameworkProfile, payload: Dict[str, List[Dict[str, str]]]) -> List[Path]:
        written_paths: List[Path] = []
        root_resolved = framework.root.resolve()
        for files in payload.values():
            for file_obj in files:
                rel_path = Path(file_obj["path"])
                target = (framework.root / rel_path).resolve()
                if os.path.commonpath([root_resolved, target]) != str(root_resolved):
                    raise ValueError(f"Attempted to write outside repo root: {rel_path}")
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(file_obj["content"], encoding="utf-8")
                written_paths.append(target)
        return written_paths

    @staticmethod
    def push_changes(framework: FrameworkProfile, branch: str, commit_msg: str) -> bool:
        return push_to_git(str(framework.root), branch=branch, commit_msg=commit_msg)


def initialise_agentic_state() -> Dict[str, Any]:
    return {
        "active": False,
        "scenario": "",
        "status": "idle",
        "preview": "",
        "feedback": [],
        "context": {},
        "payload": {},
        "written_files": [],
        "pending_test_ids": [],
        "pending_datasheet_defaults": None,
        "datasheet_values": None,
        "awaiting_datasheet": False,
    }


def interpret_confirmation(text: str) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in ["confirm", "looks good", "proceed", "go ahead", "approved"])


def interpret_push(text: str) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in ["push", "commit", "publish", "merge", "deploy"])


def interpret_feedback(text: str) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in ["feedback", "change", "modify", "update", "adjust", "revise"])
