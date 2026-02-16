"""Test suite for enhanced recorder components.

Run with:
    pytest tests/test_enhanced_recorder.py -v
"""

import json
from pathlib import Path
from unittest.mock import Mock, MagicMock

import pytest


def test_enhanced_js_injection_available():
    """Test that enhanced JS injection module is available."""
    from app.recorder.enhanced_js_injection import get_enhanced_capture_script
    
    script = get_enhanced_capture_script()
    assert script is not None
    assert len(script) > 1000
    assert "PriorityQueue" in script
    assert "IndexedDB" in script
    assert "pythonRecorderCapture" in script


def test_enhanced_capture_agent_initialization():
    """Test EnhancedCaptureAgent can be initialized."""
    from app.recorder.enhanced_capture_agent import EnhancedCaptureAgent
    
    mock_page = Mock()
    session_dir = Path("test_session")
    
    agent = EnhancedCaptureAgent(mock_page, session_dir)
    
    assert agent.page == mock_page
    assert agent.session_dir == session_dir
    assert agent.is_active == False
    assert len(agent.events_queue) == 0


def test_enhanced_capture_agent_priority():
    """Test priority assignment in EnhancedCaptureAgent."""
    from app.recorder.enhanced_capture_agent import EnhancedCaptureAgent
    
    agent = EnhancedCaptureAgent(Mock(), Path("test"))
    
    # Test priority levels
    assert agent._get_priority("navigate") == 100  # Critical
    assert agent._get_priority("submit") == 100    # Critical
    assert agent._get_priority("click") == 50      # High
    assert agent._get_priority("input") == 50      # High
    assert agent._get_priority("hover") == 20      # Medium
    assert agent._get_priority("scroll") == 5      # Low


def test_enhanced_capture_agent_element_signature():
    """Test element signature generation for deduplication."""
    from app.recorder.enhanced_capture_agent import EnhancedCaptureAgent
    
    agent = EnhancedCaptureAgent(Mock(), Path("test"))
    
    # Test with ID
    element1 = {"id": "submit-btn", "xpath": "/html/body/button[1]"}
    sig1 = agent._create_element_signature(element1)
    assert "id:submit-btn" in sig1
    
    # Test with multiple identifiers
    element2 = {
        "id": "input1",
        "name": "username",
        "dataTestId": "login-input"
    }
    sig2 = agent._create_element_signature(element2)
    assert "id:input1" in sig2
    assert "name:username" in sig2
    assert "testid:login-input" in sig2


def test_enhanced_capture_agent_add_event():
    """Test adding events with deduplication."""
    from app.recorder.enhanced_capture_agent import EnhancedCaptureAgent
    
    agent = EnhancedCaptureAgent(Mock(), Path("test"))
    
    # Add first event
    added1 = agent.add_event(
        action="click",
        timestamp=1000.0,
        element_data={"id": "btn1", "xpath": "/html/body/button"},
        extra={},
        page_url="https://example.com",
        page_title="Test Page"
    )
    assert added1 == True
    assert len(agent.events_queue) == 1
    
    # Add duplicate (same element, same action, similar timestamp)
    added2 = agent.add_event(
        action="click",
        timestamp=1050.0,  # Within 100ms window
        element_data={"id": "btn1", "xpath": "/html/body/button"},
        extra={},
        page_url="https://example.com",
        page_title="Test Page"
    )
    assert added2 == False  # Duplicate filtered
    assert len(agent.events_queue) == 1


def test_ai_verification_agent_initialization():
    """Test AIVerificationAgent initialization."""
    from app.recorder.ai_verification_agent import AIVerificationAgent
    
    agent = AIVerificationAgent(deployment_name="test-gpt4", temperature=0.1)
    assert agent is not None


def test_ai_verification_agent_heuristic_analysis():
    """Test heuristic analysis fallback."""
    from app.recorder.ai_verification_agent import AIVerificationAgent
    
    agent = AIVerificationAgent()
    agent.llm = None  # Force heuristic mode
    
    # Test with clean recording
    events = [
        {"action": "click", "timestamp": 1000},
        {"action": "input", "timestamp": 2000},
        {"action": "submit", "timestamp": 3000}
    ]
    dom_mutations = []
    snapshots = []
    
    result = agent._heuristic_analysis(events, dom_mutations, snapshots)
    
    assert result.has_gaps == False
    assert result.confidence > 0.8
    assert len(result.recommendations) > 0


def test_ai_verification_agent_orphan_detection():
    """Test orphan DOM mutation detection."""
    from app.recorder.ai_verification_agent import AIVerificationAgent
    
    agent = AIVerificationAgent()
    agent.llm = None
    
    # Events at t=1000, 2000
    events = [
        {"action": "click", "timestamp": 1000},
        {"action": "submit", "timestamp": 2000}
    ]
    
    # Mutations at t=1500 (has matching event), t=5000 (orphan)
    dom_mutations = [
        {"timestamp": 1500, "type": "childList"},
        {"timestamp": 5000, "type": "childList"},  # Orphan
        {"timestamp": 5100, "type": "attributes"},  # Orphan
    ]
    
    snapshots = []
    
    result = agent._heuristic_analysis(events, dom_mutations, snapshots)
    
    # Should detect gaps due to orphan mutations
    assert result.has_gaps == True
    assert any("DOM changes without corresponding events" in str(step) 
               for step in result.missing_steps)


def test_enhanced_recorder_integration_feature_check():
    """Test feature availability check."""
    from app.recorder.enhanced_recorder_integration import is_enhancement_available
    
    status = is_enhancement_available()
    
    assert isinstance(status, dict)
    assert "enhanced_capture" in status
    assert "ai_verification" in status
    assert "enhanced_js" in status
    assert "all_features" in status


def test_captured_event_dataclass():
    """Test CapturedEvent dataclass."""
    from app.recorder.enhanced_capture_agent import CapturedEvent
    
    event = CapturedEvent(
        action="click",
        timestamp=1000.0,
        element_signature="id:button1",
        extra={},
        page_url="https://example.com",
        page_title="Test",
        priority=50
    )
    
    assert event.action == "click"
    assert event.priority == 50
    assert event.verified == False


def test_gap_detection_result_dataclass():
    """Test GapDetectionResult dataclass."""
    from app.recorder.ai_verification_agent import GapDetectionResult
    
    result = GapDetectionResult(
        has_gaps=True,
        confidence=0.85,
        missing_steps=[{"action": "click"}],
        recommendations=["Re-record section 2"],
        analysis_summary="Gaps detected in authentication flow"
    )
    
    assert result.has_gaps == True
    assert result.confidence == 0.85
    assert len(result.missing_steps) == 1


def test_dom_change_record_dataclass():
    """Test DOMChangeRecord dataclass."""
    from app.recorder.enhanced_capture_agent import DOMChangeRecord
    
    record = DOMChangeRecord(
        timestamp=1000.0,
        mutation_type="childList",
        target_xpath="/html/body/div[1]",
        added_nodes=["button"],
        removed_nodes=[]
    )
    
    assert record.mutation_type == "childList"
    assert len(record.added_nodes) == 1


@pytest.mark.asyncio
async def test_enhanced_recorder_session_initialization():
    """Test EnhancedRecorderSession initialization."""
    from app.recorder.enhanced_recorder_integration import EnhancedRecorderSession
    
    session_dir = Path("test_recordings/test1")
    
    session = EnhancedRecorderSession(
        session_dir=session_dir,
        capture_dom=True,
        capture_screenshots=True,
        enable_mcp=False,  # Disable to avoid dependency
        enable_ai_verification=False,
        verbose=False
    )
    
    assert session.session_dir == session_dir
    assert session.capture_dom == True
    assert session.is_recording == False
    assert session.stats["events_captured"] == 0


def test_enhanced_recorder_cli_imports():
    """Test that CLI module can be imported."""
    try:
        from app.recorder import enhanced_recorder_cli
        assert enhanced_recorder_cli is not None
    except ImportError as e:
        pytest.skip(f"CLI dependencies not available: {e}")


def test_integration_all_modules_importable():
    """Test that all enhanced recorder modules can be imported."""
    modules = [
        "app.recorder.enhanced_capture_agent",
        "app.recorder.ai_verification_agent",
        "app.recorder.enhanced_js_injection",
        "app.recorder.enhanced_recorder_integration"
    ]
    
    for module_name in modules:
        try:
            __import__(module_name)
        except ImportError as e:
            pytest.fail(f"Failed to import {module_name}: {e}")
