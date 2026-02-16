"""Post-Recording AI Verification Agent for Gap Detection.

Uses Azure OpenAI to analyze recorded flows and identify missing steps
by comparing:
- Captured events timeline
- DOM mutation records
- MCP browser snapshots
- Network activity
- Page state changes

The agent reconstructs likely missing actions and suggests where to
manually verify or re-record specific sections.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

try:
    from langchain_openai import AzureChatOpenAI
    HAS_LANGCHAIN = True
except ImportError:
    HAS_LANGCHAIN = False
    logger.warning("langchain_openai not available - AI verification disabled")


@dataclass
class GapDetectionResult:
    """Result of gap detection analysis."""
    has_gaps: bool
    confidence: float  # 0-1
    missing_steps: List[Dict[str, Any]]
    recommendations: List[str]
    analysis_summary: str


class AIVerificationAgent:
    """Agent that uses AI to detect missing steps in recordings."""
    
    def __init__(
        self,
        deployment_name: Optional[str] = None,
        temperature: float = 0.1  # Low temp for analytical tasks
    ):
        """Initialize the AI verification agent.
        
        Args:
            deployment_name: Azure OpenAI deployment name
            temperature: LLM temperature (lower = more deterministic)
        """
        self.llm: Optional[Any] = None
        
        if HAS_LANGCHAIN:
            try:
                import os
                self.llm = AzureChatOpenAI(
                    deployment_name=deployment_name or os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4"),
                    temperature=temperature,
                    max_tokens=2000
                )
                logger.info("[AIVerification] LLM initialized successfully")
            except Exception as e:
                logger.warning(f"[AIVerification] LLM init failed: {e}")
                self.llm = None
    
    def analyze_recording_for_gaps(
        self,
        events: List[Dict[str, Any]],
        dom_mutations: List[Dict[str, Any]],
        snapshots: List[Dict[str, Any]],
        network_requests: List[Dict[str, Any]]
    ) -> GapDetectionResult:
        """Analyze a recording to detect potential gaps.
        
        Args:
            events: List of captured events
            dom_mutations: List of DOM mutations
            snapshots: List of browser snapshots
            network_requests: List of network requests
            
        Returns:
            GapDetectionResult with findings
        """
        if not self.llm:
            logger.warning("[AIVerification] LLM not available, using heuristic analysis")
            return self._heuristic_analysis(events, dom_mutations, snapshots)
        
        logger.info("[AIVerification] Starting AI-powered gap detection")
        
        # Prepare context for LLM
        context = self._prepare_context(events, dom_mutations, snapshots, network_requests)
        
        # Build prompt
        prompt = self._build_gap_detection_prompt(context)
        
        try:
            # Query LLM
            response = self.llm.invoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            
            # Parse response
            result = self._parse_llm_response(content)
            
            logger.info(f"[AIVerification] Analysis complete - Gaps detected: {result.has_gaps}")
            return result
        
        except Exception as e:
            logger.error(f"[AIVerification] LLM query failed: {e}")
            return self._heuristic_analysis(events, dom_mutations, snapshots)
    
    def _prepare_context(
        self,
        events: List[Dict[str, Any]],
        dom_mutations: List[Dict[str, Any]],
        snapshots: List[Dict[str, Any]],
        network_requests: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Prepare analysis context from recording data."""
        
        # Group events by time windows (100ms windows)
        time_windows = {}
        for event in events:
            window_key = int(event['timestamp'] / 100) * 100
            if window_key not in time_windows:
                time_windows[window_key] = []
            time_windows[window_key].append(event)
        
        # Identify high-activity periods
        high_activity_windows = [
            {"time": k, "event_count": len(v), "events": v}
            for k, v in time_windows.items()
            if len(v) > 3  # More than 3 events in 100ms = high activity
        ]
        
        # Find DOM mutations without corresponding events
        orphan_mutations = []
        for mutation in dom_mutations:
            mut_time = mutation.get('timestamp', 0)
            # Check if any event exists within 50ms
            has_matching_event = any(
                abs(event['timestamp'] - mut_time) < 50
                for event in events
            )
            if not has_matching_event:
                orphan_mutations.append(mutation)
        
        # Detect navigation/page changes from network requests
        navigations = [
            req for req in network_requests
            if req.get('type') == 'document' or req.get('method') == 'POST'
        ]
        
        return {
            "total_events": len(events),
            "total_mutations": len(dom_mutations),
            "total_snapshots": len(snapshots),
            "total_network_requests": len(network_requests),
            "high_activity_windows": high_activity_windows,
            "orphan_mutations": orphan_mutations[:10],  # Limit to first 10
            "navigations": navigations,
            "event_types": list(set(e.get('action', 'unknown') for e in events)),
            "time_span_seconds": (max(e['timestamp'] for e in events) - min(e['timestamp'] for e in events)) / 1000 if events else 0
        }
    
    def _build_gap_detection_prompt(self, context: Dict[str, Any]) -> str:
        """Build the prompt for LLM gap detection."""
        
        prompt = f"""You are an expert test automation analyst. Analyze this web recording session to detect potential missing user actions.

**Recording Statistics:**
- Total events captured: {context['total_events']}
- Total DOM mutations: {context['total_mutations']}
- Time span: {context['time_span_seconds']:.1f} seconds
- Event types: {', '.join(context['event_types'])}

**High Activity Periods:**
{json.dumps(context['high_activity_windows'][:5], indent=2)}

**Orphan DOM Mutations (changes without corresponding events):**
{json.dumps(context['orphan_mutations'], indent=2)}

**Navigation Events:**
{json.dumps(context['navigations'], indent=2)}

**Analysis Task:**
1. Identify if there are likely missing user actions based on:
   - Orphan DOM mutations (DOM changed but no event captured)
   - High-density event periods (potential lost events in fast sequences)
   - Navigation jumps without corresponding user actions
   - Logical gaps in workflow (e.g., form submission without filling fields)

2. For each suspected gap, provide:
   - Timestamp range where gap likely occurred
   - Description of likely missing action
   - Confidence level (0-1)
   - Reasoning

3. Provide recommendations for:
   - Whether to re-record specific sections
   - Adjustments to recording settings
   - Manual verification checkpoints

**Response Format (JSON):**
```json
{{
  "has_gaps": true/false,
  "overall_confidence": 0.0-1.0,
  "missing_steps": [
    {{
      "timestamp_range": [start_ms, end_ms],
      "likely_action": "description",
      "confidence": 0.0-1.0,
      "reasoning": "why this gap is suspected",
      "element_hint": "likely element involved"
    }}
  ],
  "recommendations": [
    "recommendation 1",
    "recommendation 2"
  ],
  "summary": "overall analysis summary"
}}
```

Provide only the JSON response, no additional text."""
        
        return prompt
    
    def _parse_llm_response(self, response: str) -> GapDetectionResult:
        """Parse LLM JSON response into GapDetectionResult."""
        try:
            # Extract JSON from response (handle markdown code blocks)
            json_str = response.strip()
            if json_str.startswith("```json"):
                json_str = json_str[7:]
            if json_str.startswith("```"):
                json_str = json_str[3:]
            if json_str.endswith("```"):
                json_str = json_str[:-3]
            json_str = json_str.strip()
            
            data = json.loads(json_str)
            
            return GapDetectionResult(
                has_gaps=data.get('has_gaps', False),
                confidence=data.get('overall_confidence', 0.0),
                missing_steps=data.get('missing_steps', []),
                recommendations=data.get('recommendations', []),
                analysis_summary=data.get('summary', 'No summary provided')
            )
        
        except json.JSONDecodeError as e:
            logger.error(f"[AIVerification] Failed to parse LLM response: {e}")
            logger.debug(f"Response was: {response[:500]}")
            
            # Return safe fallback
            return GapDetectionResult(
                has_gaps=False,
                confidence=0.0,
                missing_steps=[],
                recommendations=["LLM response parsing failed - manual review recommended"],
                analysis_summary="Failed to parse AI analysis"
            )
    
    def _heuristic_analysis(
        self,
        events: List[Dict[str, Any]],
        dom_mutations: List[Dict[str, Any]],
        snapshots: List[Dict[str, Any]]
    ) -> GapDetectionResult:
        """Fallback heuristic analysis when LLM is unavailable."""
        logger.info("[AIVerification] Using heuristic analysis (no LLM)")
        
        missing_steps = []
        recommendations = []
        
        # Heuristic 1: Check for orphan DOM mutations
        orphan_count = 0
        for mutation in dom_mutations:
            mut_time = mutation.get('timestamp', 0)
            has_matching_event = any(
                abs(event.get('timestamp', 0) - mut_time) < 100
                for event in events
            )
            if not has_matching_event:
                orphan_count += 1
        
        if orphan_count > 5:
            missing_steps.append({
                "timestamp_range": None,
                "likely_action": f"{orphan_count} DOM changes without corresponding events",
                "confidence": 0.6,
                "reasoning": "Multiple DOM mutations detected without captured user actions"
            })
            recommendations.append("Re-record with slower actions or enable enhanced capture")
        
        # Heuristic 2: Check for high-density event periods
        if len(events) > 0:
            timestamps = sorted([e.get('timestamp', 0) for e in events])
            for i in range(len(timestamps) - 1):
                time_gap = timestamps[i + 1] - timestamps[i]
                if time_gap < 10:  # Less than 10ms between events
                    missing_steps.append({
                        "timestamp_range": [timestamps[i], timestamps[i + 1]],
                        "likely_action": "Rapid sequence - possible dropped events",
                        "confidence": 0.5,
                        "reasoning": "Events too close together, some may have been dropped"
                    })
        
        # Heuristic 3: Check event count vs time span
        if len(events) > 0:
            time_span = (max(e.get('timestamp', 0) for e in events) - min(e.get('timestamp', 0) for e in events)) / 1000
            if time_span > 30 and len(events) < 10:
                recommendations.append("Very few events for long recording - verify all actions were captured")
        
        has_gaps = len(missing_steps) > 0
        confidence = 0.7 if has_gaps else 0.9
        
        summary = f"Heuristic analysis: {'Potential gaps detected' if has_gaps else 'Recording appears complete'}. "
        summary += f"Analyzed {len(events)} events, {len(dom_mutations)} mutations, {len(snapshots)} snapshots."
        
        return GapDetectionResult(
            has_gaps=has_gaps,
            confidence=confidence,
            missing_steps=missing_steps,
            recommendations=recommendations or ["Recording appears complete"],
            analysis_summary=summary
        )
    
    def generate_verification_report(
        self,
        session_dir: Path,
        result: GapDetectionResult
    ) -> Path:
        """Generate a human-readable verification report.
        
        Args:
            session_dir: Session directory
            result: Gap detection result
            
        Returns:
            Path to generated report
        """
        report_path = session_dir / "verification_report.md"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("# Recording Verification Report\n\n")
            f.write(f"**Status:** {'⚠️ GAPS DETECTED' if result.has_gaps else '✅ PASSED'}\n\n")
            f.write(f"**Confidence:** {result.confidence:.0%}\n\n")
            
            f.write("## Analysis Summary\n\n")
            f.write(f"{result.analysis_summary}\n\n")
            
            if result.missing_steps:
                f.write("## Suspected Missing Steps\n\n")
                for i, step in enumerate(result.missing_steps, 1):
                    f.write(f"### {i}. {step['likely_action']}\n\n")
                    f.write(f"- **Confidence:** {step['confidence']:.0%}\n")
                    if step.get('timestamp_range'):
                        f.write(f"- **Time Range:** {step['timestamp_range'][0]}-{step['timestamp_range'][1]}ms\n")
                    f.write(f"- **Reasoning:** {step['reasoning']}\n")
                    if step.get('element_hint'):
                        f.write(f"- **Element:** {step['element_hint']}\n")
                    f.write("\n")
            
            f.write("## Recommendations\n\n")
            for rec in result.recommendations:
                f.write(f"- {rec}\n")
            f.write("\n")
            
            f.write("---\n\n")
            f.write("*Generated by AI Verification Agent*\n")
        
        logger.info(f"[AIVerification] Report saved to {report_path}")
        return report_path


def verify_recording_session(session_dir: Path) -> Tuple[GapDetectionResult, Path]:
    """Convenience function to verify a recording session.
    
    Args:
        session_dir: Path to recording session directory
        
    Returns:
        Tuple of (detection_result, report_path)
    """
    # Load enhanced capture report if exists
    report_path = session_dir / "enhanced_capture_report.json"
    
    if not report_path.exists():
        logger.warning(f"[AIVerification] No enhanced capture report found at {report_path}")
        # Fall back to basic metadata
        metadata_path = session_dir / "metadata.json"
        if not metadata_path.exists():
            raise FileNotFoundError(f"No recording data found in {session_dir}")
        
        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        events = metadata.get('actions', [])
        dom_mutations = []
        snapshots = []
        network_requests = []
    else:
        with open(report_path, 'r', encoding='utf-8') as f:
            report = json.load(f)
        
        events = report.get('events', [])
        dom_mutations = report.get('dom_mutations', [])
        snapshots = []  # Snapshots are large, not included in report
        network_requests = report.get('network_requests', [])
    
    # Create agent and analyze
    agent = AIVerificationAgent()
    result = agent.analyze_recording_for_gaps(
        events=events,
        dom_mutations=dom_mutations,
        snapshots=snapshots,
        network_requests=network_requests
    )
    
    # Generate report
    report_file = agent.generate_verification_report(session_dir, result)
    
    return result, report_file
