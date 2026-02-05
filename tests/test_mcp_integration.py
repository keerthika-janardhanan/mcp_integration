"""Test MCP integrations to verify configuration and functionality."""

import pytest
from pathlib import Path

def test_mcp_config_exists():
    """Test that MCP configuration file exists."""
    mcp_config = Path(__file__).parent.parent.parent / ".vscode" / "mcp.json"
    assert mcp_config.exists(), "MCP configuration file not found"


def test_mcp_client_imports():
    """Test that MCP client modules can be imported."""
    try:
        from app.core.mcp_client import (
            get_microsoft_docs_mcp,
            get_github_mcp,
            get_brave_search_mcp,
            get_filesystem_mcp
        )
        assert True
    except ImportError as e:
        pytest.fail(f"Failed to import MCP clients: {e}")


def test_microsoft_docs_mcp_initialization():
    """Test Microsoft Docs MCP client initialization."""
    from app.core.mcp_client import get_microsoft_docs_mcp
    
    docs_mcp = get_microsoft_docs_mcp()
    assert docs_mcp is not None
    assert hasattr(docs_mcp, 'search_docs')
    assert hasattr(docs_mcp, 'search_code_samples')
    assert hasattr(docs_mcp, 'fetch_doc_page')


def test_github_mcp_initialization():
    """Test GitHub MCP client initialization."""
    from app.core.mcp_client import get_github_mcp
    
    github_mcp = get_github_mcp()
    assert github_mcp is not None
    assert hasattr(github_mcp, 'search_repositories')
    assert hasattr(github_mcp, 'search_code')
    assert hasattr(github_mcp, 'clone_repository')


def test_brave_search_mcp_initialization():
    """Test Brave Search MCP client initialization."""
    from app.core.mcp_client import get_brave_search_mcp
    
    brave_mcp = get_brave_search_mcp()
    assert brave_mcp is not None
    assert hasattr(brave_mcp, 'search')
    assert hasattr(brave_mcp, 'search_locator_patterns')


def test_filesystem_mcp_initialization():
    """Test Filesystem MCP client initialization."""
    from app.core.mcp_client import get_filesystem_mcp
    
    fs_mcp = get_filesystem_mcp()
    assert fs_mcp is not None
    assert hasattr(fs_mcp, 'list_directory')
    assert hasattr(fs_mcp, 'create_directory')
    assert hasattr(fs_mcp, 'safe_write_file')


def test_playwright_mcp_recorder_initialization():
    """Test Playwright MCP recorder initialization."""
    from app.recorder.mcp_integration import get_playwright_mcp_recorder
    
    recorder = get_playwright_mcp_recorder()
    assert recorder is not None
    assert hasattr(recorder, 'enhance_recording_with_snapshots')
    assert hasattr(recorder, 'generate_locators_from_element')
    assert hasattr(recorder, 'capture_console_messages')
    assert hasattr(recorder, 'capture_network_requests')


def test_mcp_graceful_degradation():
    """Test that MCP clients degrade gracefully when servers are unavailable."""
    from app.core.mcp_client import get_microsoft_docs_mcp
    
    # Even if MCP server is not running, client should initialize
    docs_mcp = get_microsoft_docs_mcp()
    
    # Search should return empty list or default values, not raise exception
    try:
        results = docs_mcp.search_docs("test query")
        assert isinstance(results, list)
    except Exception as e:
        # If it raises an exception, it should be logged but not crash
        pytest.fail(f"MCP client should degrade gracefully: {e}")


def test_llm_client_mcp_imports():
    """Test that LLM client can import MCP dependencies."""
    try:
        from app.core.llm_client import ask_llm_to_self_heal
        assert ask_llm_to_self_heal is not None
    except ImportError as e:
        pytest.fail(f"Failed to import enhanced llm_client: {e}")


def test_framework_resolver_mcp_imports():
    """Test that framework resolver can import MCP dependencies."""
    try:
        from app.api.framework_resolver import resolve_framework_root
        assert resolve_framework_root is not None
    except ImportError as e:
        pytest.fail(f"Failed to import enhanced framework_resolver: {e}")


def test_agentic_script_agent_mcp_imports():
    """Test that agentic script agent can import MCP dependencies."""
    try:
        from app.generators.agentic_script_agent import AgenticScriptAgent
        agent = AgenticScriptAgent()
        
        # Verify MCP clients are initialized
        assert hasattr(agent, 'microsoft_docs_mcp')
        assert hasattr(agent, 'github_mcp')
        assert hasattr(agent, 'filesystem_mcp')
    except ImportError as e:
        pytest.fail(f"Failed to import enhanced agentic_script_agent: {e}")


def test_env_template_exists():
    """Test that environment template file exists."""
    env_template = Path(__file__).parent.parent.parent / ".env.template"
    assert env_template.exists(), ".env.template file not found"
    
    # Verify it contains MCP-related variables
    content = env_template.read_text()
    assert "GITHUB_TOKEN" in content
    assert "BRAVE_API_KEY" in content


def test_mcp_documentation_exists():
    """Test that MCP integration documentation exists."""
    mcp_docs = Path(__file__).parent.parent.parent / "docs" / "MCP_INTEGRATION.md"
    assert mcp_docs.exists(), "MCP integration documentation not found"


def test_setup_script_exists():
    """Test that MCP setup script exists."""
    setup_script = Path(__file__).parent.parent.parent / "setup_mcp.bat"
    assert setup_script.exists(), "MCP setup script not found"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
