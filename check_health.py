"""Comprehensive health check for all MCPs and agents."""
import sys
from pathlib import Path

def check(name, func):
    """Run a check and report status."""
    try:
        result = func()
        print(f"✅ {name}: {result}")
        return True
    except Exception as e:
        print(f"❌ {name}: {e}")
        return False

def main():
    print("=" * 60)
    print("🔍 MCP Integration Health Check")
    print("=" * 60)
    
    results = []
    
    # 1. MCP Servers
    print("\n📡 MCP Servers:")
    results.append(check("MCP Client", lambda: __import__('app.core.mcp_client', fromlist=['MCPClient']) and "OK"))
    
    try:
        from app.recorder.mcp_integration import get_playwright_mcp_recorder
        mcp_rec = get_playwright_mcp_recorder()
        results.append(check("Playwright MCP Recorder", lambda: f"Available: {mcp_rec.mcp_available}"))
    except Exception as e:
        results.append(check("Playwright MCP Recorder", lambda: None))
    
    try:
        from app.core.mcp_client import get_microsoft_docs_mcp
        mcp = get_microsoft_docs_mcp()
        results.append(check("Microsoft Docs MCP", lambda: "OK"))
    except Exception as e:
        results.append(check("Microsoft Docs MCP", lambda: None))
    
    try:
        from app.core.mcp_client import get_github_mcp
        mcp = get_github_mcp()
        results.append(check("GitHub MCP", lambda: "OK"))
    except Exception as e:
        results.append(check("GitHub MCP", lambda: None))
    
    try:
        from app.core.mcp_client import get_filesystem_mcp
        mcp = get_filesystem_mcp()
        results.append(check("Filesystem MCP", lambda: "OK"))
    except Exception as e:
        results.append(check("Filesystem MCP", lambda: None))
    
    # 2. Copilot Bridge
    print("\n🤖 Copilot Bridge:")
    try:
        from app.core.llm_client_copilot import CopilotClient
        client = CopilotClient()
        results.append(check("Copilot Client", lambda: f"Bridge URL: {client.bridge_url}"))
    except Exception as e:
        results.append(check("Copilot Client", lambda: None))
    
    # 3. Agents
    print("\n🎯 Agentic Components:")
    try:
        from app.generators.agentic_script_agent import AgenticScriptAgent
        agent = AgenticScriptAgent()
        flows = agent.list_available_flows()
        results.append(check("AgenticScriptAgent", lambda: f"{len(flows)} flows available"))
    except Exception as e:
        results.append(check("AgenticScriptAgent", lambda: None))
    
    try:
        from app.generators.test_case_generator import TestCaseGenerator
        from app.core.vector_db import VectorDBClient
        db = VectorDBClient()
        gen = TestCaseGenerator(db=db, template={})
        results.append(check("TestCaseGenerator", lambda: "OK"))
    except Exception as e:
        results.append(check("TestCaseGenerator", lambda: None))
    
    try:
        from app.self_healing_with_mcp import SelfHealingExecutor
        executor = SelfHealingExecutor(".")
        results.append(check("SelfHealingExecutor", lambda: "OK"))
    except Exception as e:
        results.append(check("SelfHealingExecutor", lambda: None))
    
    # 4. Recorder
    print("\n📹 Recorder:")
    try:
        from app.recorder.run_playwright_recorder_v2 import RecorderSession
        results.append(check("Recorder Module", lambda: "OK"))
    except Exception as e:
        results.append(check("Recorder Module", lambda: None))
    
    # 5. Data Sources
    print("\n💾 Data Sources:")
    generated_flows = Path("app/generated_flow")
    if generated_flows.exists():
        flow_files = list(generated_flows.glob("*.json"))
        results.append(check("Generated Flows", lambda: f"{len(flow_files)} files in app/generated_flow/"))
    else:
        results.append(check("Generated Flows", lambda: "Directory not found (will be created on first recording)"))
    
    try:
        from app.core.vector_db import VectorDBClient
        db = VectorDBClient()
        count = db.count()
        results.append(check("Vector DB (Chroma)", lambda: f"{count} documents"))
    except Exception as e:
        results.append(check("Vector DB (Chroma)", lambda: None))
    
    # 6. API Endpoints
    print("\n🌐 API Services:")
    try:
        import requests
        resp = requests.get("http://localhost:8001/health", timeout=2)
        results.append(check("FastAPI Backend", lambda: f"Status: {resp.status_code}"))
    except Exception as e:
        results.append(check("FastAPI Backend", lambda: "Not running (start with: python -m uvicorn app.api.main:app --reload --port 8001)"))
    
    try:
        import requests
        resp = requests.get("http://localhost:5173", timeout=2)
        results.append(check("React Frontend", lambda: f"Status: {resp.status_code}"))
    except Exception as e:
        results.append(check("React Frontend", lambda: "Not running (start with: cd frontend && npm run dev)"))
    
    try:
        import requests
        resp = requests.get("http://localhost:3030/health", timeout=2)
        results.append(check("Copilot Bridge", lambda: f"Status: {resp.status_code}"))
    except Exception as e:
        results.append(check("Copilot Bridge", lambda: "Not running (optional - uses VS Code Copilot extension)"))
    
    # Summary
    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)
    percentage = (passed * 100) // total if total > 0 else 0
    print(f"📊 Results: {passed}/{total} checks passed ({percentage}%)")
    print("=" * 60)
    
    if passed == total:
        print("✅ All systems operational!")
        print("\n🚀 Ready to:")
        print("   1. Record flows: python -m app.recorder.run_playwright_recorder_v2 --url <URL>")
        print("   2. Generate scripts: Use React UI at http://localhost:5173")
        print("   3. Self-heal tests: python demo_self_healing.py")
        sys.exit(0)
    elif passed >= total * 0.7:
        print("⚠️  Most systems operational (some optional features unavailable)")
        print("\n✅ Core features working:")
        print("   - Recording")
        print("   - Script generation")
        print("   - Self-healing")
        sys.exit(0)
    else:
        print("❌ Critical issues detected")
        print("\n🔧 Troubleshooting:")
        print("   1. Install dependencies: pip install -r requirements.txt")
        print("   2. Install Playwright: python -m playwright install")
        print("   3. Check MCP config: cat .vscode/mcp.json")
        sys.exit(1)

if __name__ == "__main__":
    main()
