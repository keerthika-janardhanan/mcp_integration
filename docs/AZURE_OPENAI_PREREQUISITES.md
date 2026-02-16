# Azure OpenAI Prerequisites

Complete checklist for setting up this Test Automation Platform with Azure OpenAI integration.

---

## 1. Azure OpenAI Service Setup

### Create Azure OpenAI Resource

1. **Azure Portal**: https://portal.azure.com/
2. **Create Resource** → Search "Azure OpenAI"
3. **Select**:
   - Subscription: Your Azure subscription
   - Resource Group: Create new or use existing
   - Region: `East US`, `West Europe`, or `Sweden Central` (GPT-4 availability)
   - Name: `your-openai-resource-name`
   - Pricing Tier: `Standard S0`

4. **Deploy Model**:
   - Go to Azure OpenAI Studio: https://oai.azure.com/
   - Navigate to **Deployments** → **Create new deployment**
   - Model: `gpt-4o` or `gpt-4-turbo` (recommended)
   - Deployment name: `GPT-4o` (or custom name)
   - Deployment type: `Standard`

5. **Get Credentials**:
   - **Endpoint**: `https://your-resource.openai.azure.com/`
   - **API Key**: Keys and Endpoint → KEY 1 (copy)
   - **Deployment Name**: From deployments page
   - **API Version**: `2024-02-15-preview`

---

## 2. Environment Variables

Create `.env` file in project root:

```env
# Azure OpenAI Configuration
AZURE_OPENAI_KEY=abc123def456...your_actual_key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=GPT-4o
OPENAI_API_VERSION=2024-02-15-preview

# GitHub Token (for MCP GitHub integration)
GITHUB_TOKEN=ghp_your_github_token

# Optional: Vector DB path
VECTOR_DB_PATH=./vector_store

# Optional: Framework repos
FRAMEWORK_REPO_ROOT=./framework_repos
```

---

## 3. Python Dependencies

Install all required packages:

```powershell
# Activate virtual environment
.\\venv\\Scripts\\activate

# Install dependencies
pip install -r requirements.txt
```

**Key packages for Azure OpenAI**:
- `openai>=0.27.0` - Azure OpenAI SDK
- `langchain` - LLM orchestration
- `langchain-openai` - OpenAI integration
- `chromadb` - Vector database
- `playwright` - Browser automation
- `fastapi` - Backend API
- `python-dotenv` - Environment variables

---

## 4. Node.js & MCP Servers

### Install Node.js
- Download: https://nodejs.org/ (v18+)
- Verify: `node --version`

### Setup MCP Servers
```powershell
# Run automated setup
.\\setup_mcp.bat
```

**MCP Servers Used**:
1. **Microsoft Docs MCP** - Playwright documentation
2. **GitHub MCP** - Repository operations
3. **Filesystem MCP** - Safe file operations
4. **Playwright Test MCP** - Browser automation

---

## 5. Playwright Browsers

Install browser binaries:

```powershell
playwright install chromium firefox webkit
```

---

## 6. GitHub Personal Access Token

Required for GitHub MCP integration:

1. **Generate Token**: https://github.com/settings/tokens
2. **Scopes Required**:
   - ✅ `repo` - Full repository access
   - ✅ `read:org` - Read organization data
3. **Copy token** → Add to `.env` as `GITHUB_TOKEN`

---

## 7. Directory Structure

Create required directories:

```powershell
mkdir recordings
mkdir framework_repos
mkdir vector_store
mkdir test_data
mkdir logs
mkdir app\\generated_flows
```

---

## 8. Azure OpenAI Usage in Project

### Features Using Azure OpenAI

| Feature | Purpose | Model Used |
|---------|---------|------------|
| **AI Test Generation** | Generate Playwright scripts from recordings | GPT-4o |
| **Self-Healing** | Fix broken locators automatically | GPT-4o |
| **Manual Test Cases** | Generate Excel test cases from flows | GPT-4o |
| **Code Analysis** | Analyze existing test frameworks | GPT-4o |
| **Locator Suggestions** | Suggest resilient locators | GPT-4o |

### Cost Estimation

**GPT-4o Pricing** (as of 2024):
- Input: $5 per 1M tokens
- Output: $15 per 1M tokens

**Typical Usage**:
- Test generation: ~5,000 tokens per flow
- Self-healing: ~3,000 tokens per fix
- Manual test cases: ~2,000 tokens per flow

**Monthly estimate** (100 flows):
- ~$5-10 for moderate usage
- ~$50-100 for heavy usage

---

## 9. Verification Checklist

Run these commands to verify setup:

```powershell
# 1. Check Python environment
python --version  # Should be 3.10+

# 2. Check Node.js
node --version  # Should be 18+

# 3. Check Playwright
playwright --version

# 4. Test Azure OpenAI connection
python -c "from app.core.llm_client import get_llm_client; client = get_llm_client(); print('✅ Azure OpenAI connected')"

# 5. Test MCP servers
python -c "from app.core.mcp_client import get_microsoft_docs_mcp; mcp = get_microsoft_docs_mcp(); print('✅ MCP connected')"

# 6. Start backend
cd app/api
uvicorn main:app --reload --port 8001

# 7. Start frontend (new terminal)
cd frontend
npm run dev
```

---

## 10. Common Issues & Solutions

### Issue: "Azure OpenAI API key not found"
**Solution**: Check `.env` file exists and `AZURE_OPENAI_KEY` is set

### Issue: "Deployment not found"
**Solution**: Verify `AZURE_OPENAI_DEPLOYMENT` matches deployment name in Azure portal

### Issue: "Rate limit exceeded"
**Solution**: 
- Check Azure OpenAI quota limits
- Upgrade to higher tier if needed
- Add retry logic (already implemented)

### Issue: "MCP server not found"
**Solution**: Run `setup_mcp.bat` to install MCP servers

### Issue: "Playwright browsers not installed"
**Solution**: Run `playwright install chromium`

---

## 11. Optional: VS Code Copilot Integration

For enhanced self-healing with Copilot:

1. **Install VS Code Copilot** extension
2. **Configure Copilot Bridge**:
   ```env
   COPILOT_BRIDGE_URL=http://localhost:3030
   ```
3. **Start bridge**: `npm run copilot-bridge`

**Note**: Self-healing works without Copilot using Azure OpenAI + Microsoft Docs MCP

---

## 12. Security Best Practices

✅ **Never commit `.env` file** to Git
✅ **Use Azure Key Vault** for production secrets
✅ **Rotate API keys** regularly
✅ **Use managed identities** in Azure deployments
✅ **Restrict GitHub token** to minimum required scopes
✅ **Enable Azure OpenAI** content filtering

---

## 13. Production Deployment

For production environments:

1. **Use Azure Key Vault**:
   ```python
   from azure.keyvault.secrets import SecretClient
   from azure.identity import DefaultAzureCredential
   
   credential = DefaultAzureCredential()
   client = SecretClient(vault_url="https://your-vault.vault.azure.net/", credential=credential)
   openai_key = client.get_secret("AZURE-OPENAI-KEY").value
   ```

2. **Enable Managed Identity** on Azure App Service
3. **Use Azure Monitor** for logging and metrics
4. **Set up Azure Application Insights** for telemetry

---

## 14. Quick Start Command

After completing all prerequisites:

```powershell
# 1. Clone and setup
git clone <repository-url>
cd mcp_integration
python -m venv venv
.\\venv\\Scripts\\activate
pip install -r requirements.txt
.\\setup_mcp.bat

# 2. Configure .env
copy .env.template .env
# Edit .env with your Azure OpenAI credentials

# 3. Install browsers
playwright install chromium

# 4. Start services
# Terminal 1: Backend
cd app/api
uvicorn main:app --reload --port 8001

# Terminal 2: Frontend
cd frontend
npm run dev

# 5. Record your first flow
python -m app.run_minimal_recorder --url "https://example.com" --session-name my-first-test
```

---

## 15. Support & Resources

- **Azure OpenAI Docs**: https://learn.microsoft.com/azure/ai-services/openai/
- **Playwright Docs**: https://playwright.dev/
- **MCP Protocol**: https://modelcontextprotocol.io/
- **Project README**: [README.md](../README.md)
- **Self-Healing Guide**: [RUNTIME_SELF_HEALING.md](RUNTIME_SELF_HEALING.md)

---

**Last Updated**: 2025-02-09
