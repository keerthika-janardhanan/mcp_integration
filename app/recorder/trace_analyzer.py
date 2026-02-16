"""Trace analyzer: Compare Playwright trace events with captured recorder actions.

This utility parses trace.zip to extract all browser events and compares them
with the actions captured by our JS recorder to identify missing steps.
"""
from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from collections import defaultdict


class TraceAnalyzer:
    """Analyze Playwright trace to find missing recorder actions."""
    
    def __init__(self, trace_path: Path, metadata_path: Path):
        self.trace_path = trace_path
        self.metadata_path = metadata_path
        self.trace_events: List[Dict[str, Any]] = []
        self.recorded_actions: List[Dict[str, Any]] = []
        self.missing_events: List[Dict[str, Any]] = []
        
    def load_trace(self) -> None:
        """Extract and parse trace.zip events."""
        if not self.trace_path.exists():
            raise FileNotFoundError(f"Trace not found: {self.trace_path}")
        
        with zipfile.ZipFile(self.trace_path, 'r') as zf:
            # Playwright trace contains trace.trace file with JSON lines
            if 'trace.trace' in zf.namelist():
                trace_data = zf.read('trace.trace').decode('utf-8')
                for line in trace_data.strip().split('\n'):
                    if line.strip():
                        try:
                            event = json.loads(line)
                            self.trace_events.append(event)
                        except json.JSONDecodeError:
                            continue
    
    def load_metadata(self) -> None:
        """Load recorded actions from metadata.json."""
        if not self.metadata_path.exists():
            raise FileNotFoundError(f"Metadata not found: {self.metadata_path}")
        
        with open(self.metadata_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.recorded_actions = data.get('actions', [])
    
    def extract_trace_interactions(self) -> List[Dict[str, Any]]:
        """Extract user interactions from trace events."""
        interactions = []
        
        for event in self.trace_events:
            event_type = event.get('type', '')
            method = event.get('method', '')
            
            # Playwright API calls
            if event_type == 'action':
                interactions.append({
                    'source': 'trace',
                    'type': method,
                    'timestamp': event.get('startTime'),
                    'selector': event.get('params', {}).get('selector'),
                    'url': event.get('params', {}).get('url'),
                    'raw': event
                })
            
            # Input events
            elif event_type == 'input':
                interactions.append({
                    'source': 'trace',
                    'type': 'input',
                    'timestamp': event.get('timestamp'),
                    'selector': event.get('selector'),
                    'value': event.get('value'),
                    'raw': event
                })
        
        return sorted(interactions, key=lambda x: x.get('timestamp', 0))
    
    def compare(self) -> Dict[str, Any]:
        """Compare trace events with recorded actions."""
        self.load_trace()
        self.load_metadata()
        
        trace_interactions = self.extract_trace_interactions()
        
        # Build timeline
        recorded_timestamps = {a.get('timestamp') for a in self.recorded_actions}
        trace_timestamps = {t.get('timestamp') for t in trace_interactions}
        
        # Find missing events (in trace but not recorded)
        missing = []
        for trace_event in trace_interactions:
            ts = trace_event.get('timestamp')
            event_type = trace_event.get('type', '')
            
            # Check if similar action was recorded within 500ms window
            found = False
            for action in self.recorded_actions:
                action_ts = action.get('timestampEpochMs', 0)
                action_type = action.get('action', '')
                
                # Match by type and time proximity
                if abs(ts - action_ts) < 500 and self._types_match(event_type, action_type):
                    found = True
                    break
            
            if not found:
                missing.append(trace_event)
        
        self.missing_events = missing
        
        return {
            'trace_events_count': len(trace_interactions),
            'recorded_actions_count': len(self.recorded_actions),
            'missing_events_count': len(missing),
            'missing_events': missing,
            'coverage_percent': (len(self.recorded_actions) / max(len(trace_interactions), 1)) * 100
        }
    
    def _types_match(self, trace_type: str, action_type: str) -> bool:
        """Check if trace event type matches recorded action type."""
        mapping = {
            'click': ['click'],
            'fill': ['input', 'change', 'fill'],
            'type': ['input', 'change'],
            'check': ['click', 'change'],
            'uncheck': ['click', 'change'],
            'selectOption': ['change', 'select'],
            'press': ['press', 'keydown'],
        }
        
        return action_type in mapping.get(trace_type, [trace_type])
    
    def generate_report(self) -> str:
        """Generate human-readable comparison report."""
        report = []
        report.append("=" * 70)
        report.append("TRACE ANALYSIS REPORT")
        report.append("=" * 70)
        report.append(f"Trace file: {self.trace_path}")
        report.append(f"Metadata file: {self.metadata_path}")
        report.append("")
        
        if not self.trace_events:
            report.append("⚠️  No trace events loaded. Run compare() first.")
            return "\n".join(report)
        
        comparison = self.compare()
        
        report.append(f"📊 Summary:")
        report.append(f"  - Trace events: {comparison['trace_events_count']}")
        report.append(f"  - Recorded actions: {comparison['recorded_actions_count']}")
        report.append(f"  - Missing events: {comparison['missing_events_count']}")
        report.append(f"  - Coverage: {comparison['coverage_percent']:.1f}%")
        report.append("")
        
        if comparison['missing_events_count'] > 0:
            report.append("❌ Missing Events (in trace but not recorded):")
            report.append("")
            for i, event in enumerate(comparison['missing_events'][:10], 1):
                report.append(f"  {i}. Type: {event.get('type')}")
                report.append(f"     Selector: {event.get('selector', 'N/A')}")
                report.append(f"     Timestamp: {event.get('timestamp')}")
                report.append(f"     URL: {event.get('url', 'N/A')}")
                report.append("")
            
            if comparison['missing_events_count'] > 10:
                report.append(f"  ... and {comparison['missing_events_count'] - 10} more")
        else:
            report.append("✅ All trace events were captured!")
        
        report.append("=" * 70)
        return "\n".join(report)


def analyze_recording(session_dir: Path) -> Dict[str, Any]:
    """Analyze a recording session for missing actions."""
    trace_path = session_dir / "trace.zip"
    metadata_path = session_dir / "metadata.json"
    
    if not trace_path.exists():
        return {"error": "trace.zip not found"}
    if not metadata_path.exists():
        return {"error": "metadata.json not found"}
    
    analyzer = TraceAnalyzer(trace_path, metadata_path)
    return analyzer.compare()


def print_analysis_report(session_dir: Path) -> None:
    """Print analysis report for a recording session."""
    trace_path = session_dir / "trace.zip"
    metadata_path = session_dir / "metadata.json"
    
    analyzer = TraceAnalyzer(trace_path, metadata_path)
    print(analyzer.generate_report())


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python -m app.recorder.trace_analyzer <session_dir>")
        sys.exit(1)
    
    session_path = Path(sys.argv[1])
    if not session_path.exists():
        print(f"Error: Session directory not found: {session_path}")
        sys.exit(1)
    
    print_analysis_report(session_path)
