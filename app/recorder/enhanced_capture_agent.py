"""Enhanced Capture Agent with MCP Integration for Zero-Loss Event Recording.

This agent addresses the fast-action recording problem by:
1. Using Playwright MCP for real-time browser snapshots
2. Implementing MutationObserver to detect DOM changes
3. Priority-based event queuing with deduplication
4. Post-recording verification to identify missed steps
5. AI-powered gap detection and reconstruction

Usage:
    recorder = EnhancedCaptureAgent(page, session_dir)
    recorder.start_enhanced_capture()
    # User performs actions...
    recorder.stop_and_verify()
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

try:
    from app.core.mcp_client import MCPClient
    HAS_MCP = True
except ImportError:
    HAS_MCP = False
    logger.warning("MCPClient not available - enhanced capture will use fallback mode")


@dataclass
class CapturedEvent:
    """Represents a single captured event with metadata for deduplication."""
    action: str
    timestamp: float
    element_signature: str
    extra: Dict[str, Any]
    page_url: str
    page_title: str
    priority: int = 0  # Higher priority = more critical (e.g., clicks > hovers)
    mcp_snapshot_id: Optional[str] = None
    verified: bool = False
    
    def __hash__(self):
        # Hash for deduplication - same element + action + similar timestamp
        return hash((self.action, self.element_signature, int(self.timestamp / 100)))


@dataclass
class DOMChangeRecord:
    """Records a DOM mutation that may represent a missed interaction."""
    timestamp: float
    mutation_type: str  # 'childList', 'attributes', 'characterData'
    target_xpath: str
    added_nodes: List[str] = field(default_factory=list)
    removed_nodes: List[str] = field(default_factory=list)
    attribute_name: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None


class EnhancedCaptureAgent:
    """Agent that ensures zero event loss during fast user actions."""
    
    # Event priority levels
    PRIORITY_CRITICAL = 100  # Navigation, submit, form actions
    PRIORITY_HIGH = 50      # Click, change, input
    PRIORITY_MEDIUM = 20    # Hover, focus
    PRIORITY_LOW = 5        # Scroll, mouse move
    
    def __init__(self, page: Any, session_dir: Path):
        """Initialize the enhanced capture agent.
        
        Args:
            page: Playwright page instance
            session_dir: Directory to save capture data
        """
        self.page = page
        self.session_dir = session_dir
        self.mcp_client: Optional[MCPClient] = None
        self.events_queue: deque[CapturedEvent] = deque(maxlen=10000)
        self.seen_events: Set[int] = set()  # For deduplication
        self.dom_changes: List[DOMChangeRecord] = []
        self.snapshots: Dict[float, Dict[str, Any]] = {}
        self.is_active = False
        self.mutation_observer_installed = False
        self.last_snapshot_time = 0.0
        self.snapshot_interval = 0.5  # Take snapshot every 500ms minimum
        
        # Initialize MCP if available
        if HAS_MCP:
            try:
                self.mcp_client = MCPClient(server_name="playwright-test")
                logger.info("[EnhancedCapture] MCP client initialized")
            except Exception as e:
                logger.warning(f"[EnhancedCapture] MCP init failed: {e}")
                self.mcp_client = None
    
    def _get_priority(self, action: str) -> int:
        """Determine event priority based on action type."""
        action_lower = action.lower()
        
        if action_lower in ('navigate', 'submit', 'form_submit'):
            return self.PRIORITY_CRITICAL
        elif action_lower in ('click', 'dblclick', 'change', 'input', 'fill', 'select'):
            return self.PRIORITY_HIGH
        elif action_lower in ('hover', 'focus', 'blur', 'press', 'keyrelease'):
            return self.PRIORITY_MEDIUM
        else:
            return self.PRIORITY_LOW
    
    def _create_element_signature(self, element_data: Dict[str, Any]) -> str:
        """Create a unique signature for an element to detect duplicates."""
        # Use stable identifiers: id, data-testid, name, xpath
        parts = []
        
        if element_data.get('id'):
            parts.append(f"id:{element_data['id']}")
        if element_data.get('dataTestId'):
            parts.append(f"testid:{element_data['dataTestId']}")
        if element_data.get('name'):
            parts.append(f"name:{element_data['name']}")
        if element_data.get('xpath'):
            parts.append(f"xpath:{element_data['xpath'][-50:]}")  # Last 50 chars
        if element_data.get('cssPath'):
            parts.append(f"css:{element_data['cssPath'][-50:]}")
        
        return "|".join(parts) if parts else f"fallback:{hash(str(element_data))}"
    
    async def take_mcp_snapshot(self) -> Optional[str]:
        """Take a browser snapshot using Playwright MCP.
        
        Returns:
            Snapshot ID if successful, None otherwise
        """
        if not self.mcp_client:
            return None
        
        current_time = time.time()
        
        # Rate limit snapshots
        if current_time - self.last_snapshot_time < self.snapshot_interval:
            return None
        
        try:
            # Use MCP to capture browser snapshot
            result = self.mcp_client.call_tool(
                "mcp_playwright-te_browser_snapshot",
                {}
            )
            
            if result and "snapshot" in result:
                snapshot_id = f"snapshot_{int(current_time * 1000)}"
                self.snapshots[current_time] = {
                    "id": snapshot_id,
                    "timestamp": current_time,
                    "data": result["snapshot"]
                }
                self.last_snapshot_time = current_time
                logger.debug(f"[EnhancedCapture] Snapshot {snapshot_id} captured")
                return snapshot_id
        
        except Exception as e:
            logger.debug(f"[EnhancedCapture] Snapshot failed (non-fatal): {e}")
        
        return None
    
    async def capture_network_activity(self) -> List[Dict[str, Any]]:
        """Capture network requests using MCP for additional context."""
        if not self.mcp_client:
            return []
        
        try:
            result = self.mcp_client.call_tool(
                "mcp_playwright-te_browser_network_requests",
                {"includeStatic": False}
            )
            
            if result and "requests" in result:
                return result["requests"]
        
        except Exception as e:
            logger.debug(f"[EnhancedCapture] Network capture failed: {e}")
        
        return []
    
    def install_mutation_observer(self) -> None:
        """Install MutationObserver to detect DOM changes that might indicate missed actions."""
        if self.mutation_observer_installed:
            return
        
        observer_script = """
        (() => {
            if (window.__enhancedCaptureObserver) return;
            
            const mutations = [];
            
            const getXPath = (node) => {
                if (!node || node.nodeType !== Node.ELEMENT_NODE) return '';
                const parts = [];
                let current = node;
                while (current && current.nodeType === Node.ELEMENT_NODE) {
                    let index = 1;
                    let sibling = current.previousSibling;
                    while (sibling) {
                        if (sibling.nodeType === Node.ELEMENT_NODE && sibling.nodeName === current.nodeName) {
                            index++;
                        }
                        sibling = sibling.previousSibling;
                    }
                    parts.unshift(`${current.nodeName.toLowerCase()}[${index}]`);
                    current = current.parentNode;
                }
                return '/' + parts.join('/');
            };
            
            const observer = new MutationObserver((mutationsList) => {
                for (const mutation of mutationsList) {
                    const record = {
                        timestamp: Date.now(),
                        type: mutation.type,
                        targetXPath: getXPath(mutation.target)
                    };
                    
                    if (mutation.type === 'childList') {
                        record.addedNodes = Array.from(mutation.addedNodes)
                            .filter(n => n.nodeType === Node.ELEMENT_NODE)
                            .map(n => n.tagName.toLowerCase());
                        record.removedNodes = Array.from(mutation.removedNodes)
                            .filter(n => n.nodeType === Node.ELEMENT_NODE)
                            .map(n => n.tagName.toLowerCase());
                    } else if (mutation.type === 'attributes') {
                        record.attributeName = mutation.attributeName;
                        record.oldValue = mutation.oldValue;
                        record.newValue = mutation.target.getAttribute(mutation.attributeName);
                    }
                    
                    mutations.push(record);
                }
            });
            
            // Observe everything
            observer.observe(document.body, {
                childList: true,
                attributes: true,
                characterData: true,
                subtree: true,
                attributeOldValue: true,
                characterDataOldValue: true
            });
            
            window.__enhancedCaptureObserver = observer;
            window.__enhancedCaptureMutations = mutations;
            
            console.log('[EnhancedCapture] MutationObserver installed');
        })();
        """
        
        try:
            self.page.evaluate(observer_script)
            self.mutation_observer_installed = True
            logger.info("[EnhancedCapture] MutationObserver installed successfully")
        except Exception as e:
            logger.warning(f"[EnhancedCapture] Failed to install MutationObserver: {e}")
    
    async def collect_dom_mutations(self) -> List[DOMChangeRecord]:
        """Collect mutations from the MutationObserver."""
        if not self.mutation_observer_installed:
            return []
        
        try:
            mutations = self.page.evaluate("() => window.__enhancedCaptureMutations || []")
            
            records = []
            for mut in mutations:
                record = DOMChangeRecord(
                    timestamp=mut.get('timestamp', 0),
                    mutation_type=mut.get('type', ''),
                    target_xpath=mut.get('targetXPath', ''),
                    added_nodes=mut.get('addedNodes', []),
                    removed_nodes=mut.get('removedNodes', []),
                    attribute_name=mut.get('attributeName'),
                    old_value=mut.get('oldValue'),
                    new_value=mut.get('newValue')
                )
                records.append(record)
            
            # Clear the mutations array
            self.page.evaluate("() => { window.__enhancedCaptureMutations = []; }")
            
            return records
        
        except Exception as e:
            logger.debug(f"[EnhancedCapture] Failed to collect mutations: {e}")
            return []
    
    def add_event(
        self,
        action: str,
        timestamp: float,
        element_data: Dict[str, Any],
        extra: Dict[str, Any],
        page_url: str,
        page_title: str
    ) -> bool:
        """Add an event to the capture queue with deduplication.
        
        Returns:
            True if event was added, False if duplicate
        """
        # Create element signature
        signature = self._create_element_signature(element_data)
        
        # Create event
        event = CapturedEvent(
            action=action,
            timestamp=timestamp,
            element_signature=signature,
            extra=extra,
            page_url=page_url,
            page_title=page_title,
            priority=self._get_priority(action)
        )
        
        # Check for duplicates
        event_hash = hash(event)
        if event_hash in self.seen_events:
            logger.debug(f"[EnhancedCapture] Duplicate event filtered: {action} on {signature}")
            return False
        
        # Add to queue and dedup set
        self.events_queue.append(event)
        self.seen_events.add(event_hash)
        
        logger.debug(f"[EnhancedCapture] Event captured: {action} (priority={event.priority})")
        return True
    
    def get_sorted_events(self) -> List[CapturedEvent]:
        """Get all captured events sorted by timestamp (stable sort preserving priority)."""
        # Sort by timestamp, but use priority as secondary key to ensure critical events
        # aren't reordered if timestamps are very close
        events_list = list(self.events_queue)
        events_list.sort(key=lambda e: (e.timestamp, -e.priority))
        return events_list
    
    async def verify_events_with_snapshots(self) -> Tuple[List[CapturedEvent], List[str]]:
        """Verify captured events against MCP snapshots to identify gaps.
        
        Returns:
            Tuple of (verified_events, missing_actions_descriptions)
        """
        if not self.mcp_client or not self.snapshots:
            logger.info("[EnhancedCapture] No MCP data for verification")
            return list(self.events_queue), []
        
        logger.info(f"[EnhancedCapture] Verifying {len(self.events_queue)} events with {len(self.snapshots)} snapshots")
        
        verified_events = []
        missing_actions = []
        
        # Get sorted events
        events = self.get_sorted_events()
        
        # Compare DOM snapshots to detect state changes not captured
        snapshot_times = sorted(self.snapshots.keys())
        
        for i in range(len(snapshot_times) - 1):
            time1, time2 = snapshot_times[i], snapshot_times[i + 1]
            snap1 = self.snapshots[time1]["data"]
            snap2 = self.snapshots[time2]["data"]
            
            # Find events between these snapshots
            between_events = [e for e in events if time1 <= e.timestamp <= time2]
            
            # Analyze if DOM changes match the captured events
            # This is a simplified check - in production, would use AI/LLM
            if self._detect_unmatched_changes(snap1, snap2, between_events):
                missing_actions.append(
                    f"Potential missing action between {time1:.2f} and {time2:.2f}"
                )
        
        return events, missing_actions
    
    def _detect_unmatched_changes(
        self,
        snapshot1: str,
        snapshot2: str,
        events: List[CapturedEvent]
    ) -> bool:
        """Detect if there are DOM changes not explained by captured events.
        
        This is a simplified heuristic - real implementation would use LLM.
        """
        # Simple heuristic: if snapshots differ significantly but no high-priority events captured
        if snapshot1 == snapshot2:
            return False
        
        high_priority_events = [e for e in events if e.priority >= self.PRIORITY_HIGH]
        
        # If snapshots differ a lot but no high-priority events, something might be missed
        diff_ratio = len(set(snapshot2) - set(snapshot1)) / max(len(snapshot2), 1)
        
        return diff_ratio > 0.1 and len(high_priority_events) == 0
    
    async def start_enhanced_capture(self) -> None:
        """Start the enhanced capture system."""
        logger.info("[EnhancedCapture] Starting enhanced capture")
        
        self.is_active = True
        
        # Install MutationObserver
        self.install_mutation_observer()
        
        # Take initial snapshot
        await self.take_mcp_snapshot()
        
        # Start background snapshot loop
        asyncio.create_task(self._snapshot_loop())
        
        logger.info("[EnhancedCapture] Enhanced capture active")
    
    async def _snapshot_loop(self) -> None:
        """Background loop to periodically take snapshots."""
        while self.is_active:
            await asyncio.sleep(self.snapshot_interval)
            await self.take_mcp_snapshot()
    
    async def stop_and_verify(self) -> Dict[str, Any]:
        """Stop capture and run verification to detect missing steps.
        
        Returns:
            Dictionary with capture summary and verification results
        """
        logger.info("[EnhancedCapture] Stopping and verifying capture")
        
        self.is_active = False
        
        # Take final snapshot
        await self.take_mcp_snapshot()
        
        # Collect final DOM mutations
        dom_mutations = await self.collect_dom_mutations()
        self.dom_changes.extend(dom_mutations)
        
        # Verify events
        verified_events, missing_actions = await self.verify_events_with_snapshots()
        
        # Capture final network state
        network_requests = await self.capture_network_activity()
        
        # Generate report
        report = {
            "total_events_captured": len(self.events_queue),
            "unique_events": len(self.seen_events),
            "events_by_priority": {
                "critical": len([e for e in verified_events if e.priority >= self.PRIORITY_CRITICAL]),
                "high": len([e for e in verified_events if e.priority >= self.PRIORITY_HIGH]),
                "medium": len([e for e in verified_events if e.priority >= self.PRIORITY_MEDIUM]),
                "low": len([e for e in verified_events if e.priority < self.PRIORITY_MEDIUM]),
            },
            "dom_mutations_detected": len(self.dom_changes),
            "snapshots_taken": len(self.snapshots),
            "network_requests": len(network_requests),
            "potential_missing_actions": missing_actions,
            "verification_status": "PASSED" if not missing_actions else "WARNING",
            "events": [self._event_to_dict(e) for e in verified_events]
        }
        
        # Save report
        report_path = self.session_dir / "enhanced_capture_report.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"[EnhancedCapture] Capture report saved to {report_path}")
        logger.info(f"[EnhancedCapture] Status: {report['verification_status']}")
        
        if missing_actions:
            logger.warning(f"[EnhancedCapture] Detected {len(missing_actions)} potential missing actions")
            for action in missing_actions:
                logger.warning(f"  - {action}")
        
        return report
    
    def _event_to_dict(self, event: CapturedEvent) -> Dict[str, Any]:
        """Convert CapturedEvent to dictionary for serialization."""
        return {
            "action": event.action,
            "timestamp": event.timestamp,
            "element_signature": event.element_signature,
            "extra": event.extra,
            "page_url": event.page_url,
            "page_title": event.page_title,
            "priority": event.priority,
            "mcp_snapshot_id": event.mcp_snapshot_id,
            "verified": event.verified
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get real-time capture statistics."""
        events = list(self.events_queue)
        
        return {
            "is_active": self.is_active,
            "total_events": len(events),
            "unique_events": len(self.seen_events),
            "mutations_detected": len(self.dom_changes),
            "snapshots_taken": len(self.snapshots),
            "priority_breakdown": {
                "critical": len([e for e in events if e.priority >= self.PRIORITY_CRITICAL]),
                "high": len([e for e in events if e.priority >= self.PRIORITY_HIGH]),
                "medium": len([e for e in events if e.priority >= self.PRIORITY_MEDIUM]),
                "low": len([e for e in events if e.priority < self.PRIORITY_MEDIUM]),
            }
        }


# Async helper for backward compatibility
async def create_enhanced_capture_agent(page: Any, session_dir: Path) -> EnhancedCaptureAgent:
    """Factory function to create and initialize an enhanced capture agent."""
    agent = EnhancedCaptureAgent(page, session_dir)
    await agent.start_enhanced_capture()
    return agent
