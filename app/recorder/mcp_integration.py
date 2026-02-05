"""Enhanced recorder integration with Playwright MCP for better test generation.

Integrates Playwright Test MCP with JS injection recording for:
- Real-time event capture (JS injection - primary)
- Rich accessibility snapshots (MCP enhancement)
- Multiple locator strategies (MCP generation)
- Console/network diagnostics (MCP capture)

MCP calls are optional and gracefully degrade if unavailable.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    from app.core.mcp_client import MCPClient
    HAS_MCP_CLIENT = True
except ImportError:
    HAS_MCP_CLIENT = False
    logger.warning("MCPClient not available - MCP integration disabled")

class PlaywrightMCPRecorder:
    """Wrapper for integrating Playwright Test MCP with the recorder."""
    
    def __init__(self):
        self.mcp_available = self._check_mcp_availability()
        self.mcp_client: Optional[Any] = None
        if self.mcp_available and HAS_MCP_CLIENT:
            try:
                # Initialize Playwright MCP client
                self.mcp_client = MCPClient(server_name="playwright-test")
                logger.info("[PlaywrightMCP] Initialized MCP client successfully")
            except Exception as e:
                logger.warning(f"[PlaywrightMCP] Failed to initialize MCP client: {e}")
                self.mcp_available = False
        
    def _check_mcp_availability(self) -> bool:
        """Check if Playwright Test MCP server is configured."""
        try:
            config_path = Path(__file__).parent.parent.parent / ".vscode" / "mcp.json"
            if config_path.exists():
                import json
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    return 'playwright-test' in config.get('servers', {})
            return False
        except Exception as e:
            logger.warning(f"Could not check MCP availability: {e}")
            return False
    
    def enhance_recording_with_snapshots(self, page: Any, step_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance recorded step with Playwright MCP browser snapshot data.
        
        Args:
            page: Playwright page object
            step_data: Current step data from recorder
            
        Returns:
            Enhanced step data with MCP snapshot information (accessibility tree, computed styles)
        """
        if not self.mcp_available or not self.mcp_client:
            logger.debug("Playwright MCP not available, skipping snapshot enhancement")
            return step_data
        
        try:
            # Call browser_snapshot MCP tool to get rich accessibility tree
            logger.debug("[PlaywrightMCP] Capturing browser snapshot for step enhancement")
            
            snapshot_result = self.mcp_client.call_tool(
                "mcp_microsoft_pla_browser_snapshot",
                {"includeStyles": True}  # Include computed styles
            )
            
            if snapshot_result and "snapshot" in snapshot_result:
                # Add accessibility tree to step data
                step_data['mcp_snapshot'] = snapshot_result['snapshot']
                step_data['mcp_enhanced'] = True
                logger.debug("[PlaywrightMCP] Added accessibility snapshot to step")
            
            return step_data
            
        except Exception as e:
            logger.debug(f"[PlaywrightMCP] Snapshot enhancement failed (non-fatal): {e}")
            return step_data
    
    def generate_locators_from_element(self, element_selector: str, page: Any, element_ref: Optional[str] = None) -> Dict[str, str]:
        """Generate multiple locator strategies for an element using Playwright MCP.
        
        Args:
            element_selector: Current element selector (from JS)
            page: Playwright page object
            element_ref: Element reference from snapshot (if available)
            
        Returns:
            Dictionary with multiple locator strategies (role, label, text, css, xpath)
        """
        if not self.mcp_available or not self.mcp_client:
            return {"css": element_selector}
        
        try:
            # Call browser_generate_locator MCP tool
            logger.debug(f"[PlaywrightMCP] Generating alternative locators for: {element_selector}")
            
            params = {
                "element": element_selector,
                "ref": element_ref or element_selector
            }
            
            result = self.mcp_client.call_tool(
                "mcp_playwright-te_browser_generate_locator",
                params
            )
            
            if result and "locator" in result:
                # MCP returns Playwright locator code - parse it
                locator_code = result["locator"]
                return {
                    "css": element_selector,  # Keep original from JS
                    "playwright_code": locator_code,  # Generated by MCP
                    "mcp_enhanced": True
                }
            
            return {"css": element_selector}
            
        except Exception as e:
            logger.debug(f"[PlaywrightMCP] Locator generation failed (non-fatal): {e}")
            return {"css": element_selector}
    
    def capture_console_messages(self, page: Any, level: str = "info") -> List[Dict[str, Any]]:
        """Capture console messages using Playwright MCP.
        
        Args:
            page: Playwright page object
            level: Minimum log level (error, warning, info, debug)
            
        Returns:
            List of console messages with metadata
        """
        if not self.mcp_available or not self.mcp_client:
            return []
        
        try:
            # Call browser_console_messages MCP tool
            logger.debug("[PlaywrightMCP] Capturing console messages")
            
            result = self.mcp_client.call_tool(
                "mcp_microsoft_pla_browser_console_messages",
                {"level": level}
            )
            
            if result and "messages" in result:
                messages = result["messages"]
                logger.debug(f"[PlaywrightMCP] Captured {len(messages)} console messages")
                return messages
            
            return []
            
        except Exception as e:
            logger.debug(f"[PlaywrightMCP] Console capture failed (non-fatal): {e}")
            return []
    
    def capture_network_requests(self, page: Any, include_static: bool = False) -> List[Dict[str, Any]]:
        """Capture network requests using Playwright MCP.
        
        Args:
            page: Playwright page object
            include_static: Include static resources (images, fonts, etc.)
            
        Returns:
            List of network requests with metadata
        """
        if not self.mcp_available or not self.mcp_client:
            return []
        
        try:
            # Call browser_network_requests MCP tool
            logger.debug("[PlaywrightMCP] Capturing network requests")
            
            result = self.mcp_client.call_tool(
                "mcp_microsoft_pla_browser_network_requests",
                {"includeStatic": include_static}
            )
            
            if result and "requests" in result:
                requests = result["requests"]
                logger.debug(f"[PlaywrightMCP] Captured {len(requests)} network requests")
                return requests
            
            return []
            
        except Exception as e:
            logger.debug(f"[PlaywrightMCP] Network capture failed (non-fatal): {e}")
            return []
    
    def evaluate_element_properties(self, page: Any, selector: str, element_ref: Optional[str] = None) -> Dict[str, Any]:
        """Evaluate element properties using Playwright MCP.
        
        Args:
            page: Playwright page object
            selector: Element selector
            element_ref: Element reference from snapshot (if available)
            
        Returns:
            Dictionary of element properties (bounding box, computed styles, attributes)
        """
        if not self.mcp_available or not self.mcp_client:
            return {}
        
        try:
            # Call browser_evaluate MCP tool
            logger.debug(f"[PlaywrightMCP] Evaluating element: {selector}")
            
            # JavaScript function to get element properties
            eval_function = """
            (element) => {
                const rect = element.getBoundingClientRect();
                const computedStyle = window.getComputedStyle(element);
                return {
                    boundingBox: {
                        x: rect.x,
                        y: rect.y,
                        width: rect.width,
                        height: rect.height
                    },
                    visible: rect.width > 0 && rect.height > 0 && computedStyle.visibility !== 'hidden',
                    enabled: !element.disabled && computedStyle.pointerEvents !== 'none',
                    tagName: element.tagName.toLowerCase(),
                    attributes: Array.from(element.attributes).reduce((acc, attr) => {
                        acc[attr.name] = attr.value;
                        return acc;
                    }, {})
                };
            }
            """
            
            params = {
                "function": eval_function,
                "element": selector
            }
            if element_ref:
                params["ref"] = element_ref
            
            result = self.mcp_client.call_tool(
                "mcp_microsoft_pla_browser_evaluate",
                params
            )
            
            if result and "result" in result:
                return result["result"]
            
            return {}
            
        except Exception as e:
            logger.debug(f"[PlaywrightMCP] Element evaluation failed (non-fatal): {e}")
            return {}
    
    def enhance_metadata_with_mcp(self, metadata: Dict[str, Any], page: Any) -> Dict[str, Any]:
        """Enhance recording metadata with Playwright MCP data.
        
        Args:
            metadata: Current metadata dictionary
            page: Playwright page object
            
        Returns:
            Enhanced metadata with MCP information
        """
        if not self.mcp_available:
            logger.debug("Playwright MCP not available for metadata enhancement")
            return metadata
        
        try:
            # Capture console messages
            console_messages = self.capture_console_messages(page)
            if console_messages:
                metadata['mcp_console_messages'] = console_messages
            
            # Capture network requests (exclude static resources for cleaner data)
            network_requests = self.capture_network_requests(page, include_static=False)
            if network_requests:
                metadata['mcp_network_requests'] = network_requests
            
            # Add MCP integration metadata
            metadata['mcp_integration'] = {
                'enabled': True,
                'version': '1.0',
                'features': [
                    'browser_snapshot',
                    'locator_generation',
                    'console_messages',
                    'network_requests',
                    'element_evaluation'
                ]
            }
            
            logger.info("[PlaywrightMCP] Enhanced metadata with MCP data")
            return metadata
            
        except Exception as e:
            logger.warning(f"[PlaywrightMCP] Metadata enhancement failed: {e}")
            return metadata


# Singleton instance
_playwright_mcp_recorder: Optional[PlaywrightMCPRecorder] = None


def get_playwright_mcp_recorder() -> PlaywrightMCPRecorder:
    """Get or create Playwright MCP Recorder singleton."""
    global _playwright_mcp_recorder
    if _playwright_mcp_recorder is None:
        _playwright_mcp_recorder = PlaywrightMCPRecorder()
    return _playwright_mcp_recorder


def enhance_recorder_step(step_data: Dict[str, Any], page: Any) -> Dict[str, Any]:
    """Convenience function to enhance a recorder step with Playwright MCP.
    
    Args:
        step_data: Step data from recorder
        page: Playwright page object
        
    Returns:
        Enhanced step data
    """
    recorder = get_playwright_mcp_recorder()
    return recorder.enhance_recording_with_snapshots(page, step_data)


def enhance_recorder_metadata(metadata: Dict[str, Any], page: Any) -> Dict[str, Any]:
    """Convenience function to enhance recorder metadata with Playwright MCP.
    
    Args:
        metadata: Metadata from recorder
        page: Playwright page object
        
    Returns:
        Enhanced metadata
    """
    recorder = get_playwright_mcp_recorder()
    return recorder.enhance_metadata_with_mcp(metadata, page)
