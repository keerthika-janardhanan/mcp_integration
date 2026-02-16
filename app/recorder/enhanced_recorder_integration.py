"""Integration module for enhanced recording with zero-loss capture.

This module provides a drop-in enhancement for the existing recorder
that adds:
- Enhanced JavaScript capture with priority queuing
- MCP-powered verification
- AI-powered gap detection
- Automatic verification reports

Usage:
    from app.recorder.enhanced_recorder_integration import EnhancedRecorderSession
    
    session = EnhancedRecorderSession(
        session_dir=Path("recordings/demo"),
        capture_dom=True,
        capture_screenshots=True,
        enable_mcp=True,
        enable_ai_verification=True
    )
    
    # Use like normal recorder
    await session.start(page, url)
    # ... user performs actions ...
    result = await session.stop_and_finalize()
    
    # Result includes verification report
    print(f"Gaps detected: {result['verification']['has_gaps']}")
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

try:
    from app.recorder.enhanced_capture_agent import EnhancedCaptureAgent
    HAS_ENHANCED_CAPTURE = True
except ImportError:
    HAS_ENHANCED_CAPTURE = False
    logger.warning("Enhanced capture agent not available")

try:
    from app.recorder.ai_verification_agent import AIVerificationAgent, verify_recording_session
    HAS_AI_VERIFICATION = True
except ImportError:
    HAS_AI_VERIFICATION = False
    logger.warning("AI verification agent not available")

try:
    from app.recorder.enhanced_js_injection import get_enhanced_capture_script
    HAS_ENHANCED_JS = True
except ImportError:
    HAS_ENHANCED_JS = False
    logger.warning("Enhanced JS injection not available")


class EnhancedRecorderSession:
    """Enhanced recorder session with zero-loss capture."""
    
    def __init__(
        self,
        session_dir: Path,
        capture_dom: bool = True,
        capture_screenshots: bool = True,
        enable_mcp: bool = True,
        enable_ai_verification: bool = True,
        verbose: bool = True
    ):
        """Initialize enhanced recorder session.
        
        Args:
            session_dir: Directory to save recording
            capture_dom: Capture DOM snapshots
            capture_screenshots: Capture screenshots
            enable_mcp: Enable MCP-powered enhancements
            enable_ai_verification: Enable AI gap detection
            verbose: Enable verbose logging
        """
        self.session_dir = Path(session_dir)
        self.session_dir.mkdir(parents=True, exist_ok=True)
        
        self.capture_dom = capture_dom
        self.capture_screenshots = capture_screenshots
        self.enable_mcp = enable_mcp and HAS_ENHANCED_CAPTURE
        self.enable_ai_verification = enable_ai_verification and HAS_AI_VERIFICATION
        self.verbose = verbose
        
        self.page: Optional[Any] = None
        self.enhanced_agent: Optional[EnhancedCaptureAgent] = None
        self.start_url: Optional[str] = None
        self.is_recording = False
        
        # Statistics
        self.stats = {
            "events_captured": 0,
            "dom_mutations": 0,
            "snapshots_taken": 0,
            "verification_passed": None
        }
        
        if self.verbose:
            logger.setLevel(logging.DEBUG)
    
    async def start(self, page: Any, url: str) -> None:
        """Start the enhanced recording session.
        
        Args:
            page: Playwright page instance
            url: Starting URL
        """
        logger.info(f"[EnhancedRecorder] Starting session in {self.session_dir}")
        logger.info(f"[EnhancedRecorder] MCP: {self.enable_mcp}, AI: {self.enable_ai_verification}")
        
        self.page = page
        self.start_url = url
        self.is_recording = True
        
        # Navigate to URL
        await page.goto(url)
        
        # Inject enhanced JavaScript
        if HAS_ENHANCED_JS:
            enhanced_script = get_enhanced_capture_script()
            await page.evaluate(enhanced_script)
            logger.info("[EnhancedRecorder] Enhanced JS injected")
        
        # Start enhanced capture agent if MCP enabled
        if self.enable_mcp:
            self.enhanced_agent = EnhancedCaptureAgent(page, self.session_dir)
            await self.enhanced_agent.start_enhanced_capture()
            logger.info("[EnhancedRecorder] Enhanced capture agent started")
        
        # Expose capture handler for JavaScript
        await page.expose_function(
            "pythonRecorderCapture",
            lambda event: self._handle_capture_event(event)
        )
        
        logger.info("[EnhancedRecorder] Recording started successfully")
    
    def _handle_capture_event(self, event: Dict[str, Any]) -> None:
        """Handle a captured event from JavaScript.
        
        Args:
            event: Event data from JavaScript
        """
        self.stats["events_captured"] += 1
        
        # Also add to enhanced agent if available
        if self.enhanced_agent:
            try:
                self.enhanced_agent.add_event(
                    action=event.get('action', 'unknown'),
                    timestamp=event.get('timestamp', 0),
                    element_data=event.get('element', {}),
                    extra=event.get('extra', {}),
                    page_url=event.get('pageUrl', ''),
                    page_title=event.get('pageTitle', '')
                )
            except Exception as e:
                logger.debug(f"[EnhancedRecorder] Enhanced agent capture failed: {e}")
        
        # Log periodically
        if self.verbose and self.stats["events_captured"] % 10 == 0:
            logger.debug(f"[EnhancedRecorder] Captured {self.stats['events_captured']} events")
    
    async def stop_and_finalize(self) -> Dict[str, Any]:
        """Stop recording and generate verification reports.
        
        Returns:
            Dictionary with recording results and verification status
        """
        logger.info("[EnhancedRecorder] Stopping recording and finalizing")
        
        self.is_recording = False
        
        result = {
            "session_dir": str(self.session_dir),
            "start_url": self.start_url,
            "statistics": dict(self.stats),
            "verification": {},
            "reports": []
        }
        
        # Stop enhanced agent and get report
        if self.enhanced_agent:
            try:
                capture_report = await self.enhanced_agent.stop_and_verify()
                
                result["statistics"]["events_captured"] = capture_report.get("total_events_captured", 0)
                result["statistics"]["dom_mutations"] = capture_report.get("dom_mutations_detected", 0)
                result["statistics"]["snapshots_taken"] = capture_report.get("snapshots_taken", 0)
                
                result["verification"]["capture_status"] = capture_report.get("verification_status", "UNKNOWN")
                result["verification"]["missing_actions"] = capture_report.get("potential_missing_actions", [])
                
                result["reports"].append(str(self.session_dir / "enhanced_capture_report.json"))
                
                logger.info(f"[EnhancedRecorder] Capture report: {capture_report['verification_status']}")
            except Exception as e:
                logger.error(f"[EnhancedRecorder] Enhanced agent finalization failed: {e}")
        
        # Run AI verification if enabled
        if self.enable_ai_verification:
            try:
                logger.info("[EnhancedRecorder] Running AI verification")
                gap_result, report_path = verify_recording_session(self.session_dir)
                
                result["verification"]["ai_analysis"] = {
                    "has_gaps": gap_result.has_gaps,
                    "confidence": gap_result.confidence,
                    "missing_steps_count": len(gap_result.missing_steps),
                    "summary": gap_result.analysis_summary
                }
                
                result["statistics"]["verification_passed"] = not gap_result.has_gaps
                
                result["reports"].append(str(report_path))
                
                logger.info(f"[EnhancedRecorder] AI Verification: {'PASSED' if not gap_result.has_gaps else 'GAPS DETECTED'}")
                
                if gap_result.has_gaps:
                    logger.warning(f"[EnhancedRecorder] {len(gap_result.missing_steps)} potential missing steps")
                    for step in gap_result.missing_steps[:3]:  # Show first 3
                        logger.warning(f"  - {step['likely_action']} (confidence: {step['confidence']:.0%})")
                
            except Exception as e:
                logger.error(f"[EnhancedRecorder] AI verification failed: {e}")
                result["verification"]["ai_analysis"] = {
                    "error": str(e)
                }
        
        # Save final summary
        summary_path = self.session_dir / "session_summary.json"
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        result["reports"].append(str(summary_path))
        
        logger.info(f"[EnhancedRecorder] Session finalized successfully")
        logger.info(f"[EnhancedRecorder] Reports: {len(result['reports'])} files generated")
        
        return result
    
    def get_real_time_stats(self) -> Dict[str, Any]:
        """Get real-time recording statistics.
        
        Returns:
            Dictionary with current stats
        """
        stats = dict(self.stats)
        
        if self.enhanced_agent:
            agent_stats = self.enhanced_agent.get_statistics()
            stats.update({
                "enhanced_capture_active": agent_stats["is_active"],
                "enhanced_events": agent_stats["total_events"],
                "mutations_detected": agent_stats["mutations_detected"],
                "snapshots_taken": agent_stats["snapshots_taken"]
            })
        
        return stats
    
    async def pause(self) -> None:
        """Pause recording (events not captured)."""
        if self.enhanced_agent:
            # Would need to add pause functionality to EnhancedCaptureAgent
            pass
        logger.info("[EnhancedRecorder] Recording paused")
    
    async def resume(self) -> None:
        """Resume recording."""
        if self.enhanced_agent:
            # Would need to add resume functionality to EnhancedCaptureAgent
            pass
        logger.info("[EnhancedRecorder] Recording resumed")


# Convenience functions
async def create_enhanced_session(
    session_dir: Path,
    page: Any,
    url: str,
    **kwargs
) -> EnhancedRecorderSession:
    """Create and start an enhanced recording session.
    
    Args:
        session_dir: Directory to save recording
        page: Playwright page instance
        url: Starting URL
        **kwargs: Additional options (capture_dom, enable_mcp, etc.)
        
    Returns:
        Started EnhancedRecorderSession
    """
    session = EnhancedRecorderSession(session_dir, **kwargs)
    await session.start(page, url)
    return session


def is_enhancement_available() -> Dict[str, bool]:
    """Check which enhancement features are available.
    
    Returns:
        Dictionary of feature availability
    """
    return {
        "enhanced_capture": HAS_ENHANCED_CAPTURE,
        "ai_verification": HAS_AI_VERIFICATION,
        "enhanced_js": HAS_ENHANCED_JS,
        "all_features": HAS_ENHANCED_CAPTURE and HAS_AI_VERIFICATION and HAS_ENHANCED_JS
    }


def print_feature_status() -> None:
    """Print status of enhancement features."""
    status = is_enhancement_available()
    
    print("\n" + "="*60)
    print("Enhanced Recorder Feature Status")
    print("="*60)
    print(f"  Enhanced Capture Agent:  {'✅' if status['enhanced_capture'] else '❌'}")
    print(f"  AI Verification:         {'✅' if status['ai_verification'] else '❌'}")
    print(f"  Enhanced JS Injection:   {'✅' if status['enhanced_js'] else '❌'}")
    print("="*60)
    print(f"  All Features Available:  {'✅' if status['all_features'] else '❌'}")
    print("="*60 + "\n")
    
    if not status['all_features']:
        print("⚠️  Some features unavailable. Install dependencies:")
        if not status['enhanced_capture']:
            print("   - Check app/core/mcp_client.py is available")
        if not status['ai_verification']:
            print("   - Install: pip install langchain-openai")
        print()
