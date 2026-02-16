# Copy-Paste Prompt for Generating VS Code Copilot Bridge

## What Your Colleague Should Do

1. **Open VS Code** (empty folder or new workspace)
2. **Open Copilot Chat** (Ctrl+Alt+I or click Copilot icon)
3. **Copy-paste this ENTIRE prompt:**

---

## PROMPT START (Copy everything below)

```
Create a complete VS Code extension that exposes GitHub Copilot Chat API via HTTP for external applications.

REQUIREMENTS:

1. Extension Details:
   - Name: "copilot-bridge"
   - Port: 3030
   - Auto-activate on startup
   - TypeScript-based

2. HTTP Endpoint:
   - POST /api/copilot/chat
   - Request body:
     {
       "messages": [
         {"role": "user", "content": "your question"},
         {"role": "assistant", "content": "previous response"},
         ...
       ],
       "temperature": 0.1
     }
   - Response:
     {
       "response": "Copilot's response text"
     }

3. Implementation:
   - Use Express.js for HTTP server
   - Use @vscode/prompt-tsx to call GitHub Copilot
   - Include body-parser middleware
   - Add CORS support
   - Comprehensive error handling
   - Console logging for debugging

4. Files to Generate:

   a) package.json:
      - Express 4.18.2
      - body-parser 1.20.2
      - @types/express, @types/node, @types/vscode as devDependencies
      - TypeScript 5.3.3
      - Compile script: "tsc -p ./"
      - vscode engine: "^1.85.0"

   b) tsconfig.json:
      - Target: ES2020
      - Module: CommonJS
      - Output: ./out
      - Strict mode enabled

   c) src/extension.ts:
      - Implement activate() function
      - Start Express server on port 3030
      - POST /api/copilot/chat endpoint
      - Use vscode.lm.sendChatRequest() or equivalent Copilot API
      - Convert streaming response to single string
      - Error handling with try-catch
      - Console.log for debugging

   d) .vscode/launch.json:
      - Run Extension configuration
      - extensionHost type
      - extensionDevelopmentPath: workspaceFolder

   e) README.md:
      - Installation steps (npm install, npm run compile)
      - How to run (F5 in VS Code)
      - How to test (curl example)
      - Troubleshooting section

   f) .vscodeignore:
      - Exclude src/, tsconfig.json, .vscode/, node_modules/

5. Key Implementation Notes:
   - Server must start immediately on extension activation
   - Use vscode.lm API for Copilot access (if available)
   - Handle streaming responses from Copilot
   - Add timeout handling (120 seconds)
   - Log all requests/responses for debugging
   - Graceful error messages

6. Testing Endpoint:
   Include a test section showing:
   - PowerShell example
   - curl example
   - Expected response format

Generate ALL files with complete, production-ready code. No placeholders or TODOs.
```

## PROMPT END

---

## After Copilot Generates the Files

Your colleague should see Copilot create these files:

```
copilot-bridge/
├── package.json
├── tsconfig.json
├── .vscodeignore
├── README.md
├── src/
│   └── extension.ts
└── .vscode/
    └── launch.json
```

## Next Steps

1. **Save all generated files** in a new folder (e.g., `C:\copilot-bridge`)

2. **Install dependencies:**
   ```powershell
   cd C:\copilot-bridge
   npm install
   ```

3. **Compile TypeScript:**
   ```powershell
   npm run compile
   ```

4. **Open folder in VS Code:**
   - File → Open Folder → Select `copilot-bridge`

5. **Run the extension:**
   - Press F5 (or Run → Start Debugging)
   - New VS Code window opens
   - Check Debug Console for: "Server running on http://localhost:3030"

6. **Test it:**
   ```powershell
   $body = @{
       messages = @(
           @{ role = "user"; content = "Say hello" }
       )
   } | ConvertTo-Json -Depth 10

   Invoke-RestMethod -Uri "http://localhost:3030/api/copilot/chat" `
       -Method POST `
       -Body $body `
       -ContentType "application/json"
   ```

## If Copilot Generates Incomplete Code

If the extension code is incomplete or has issues, ask Copilot:

```
The extension.ts file is incomplete. Please provide the complete implementation of:

1. The Express server setup with body-parser
2. The POST /api/copilot/chat route handler
3. Integration with vscode.lm API or vscode.chat API to call GitHub Copilot
4. Proper error handling and response formatting
5. Console logging for debugging

Use the @vscode/prompt-tsx package or the built-in VS Code Chat API.
Show me the COMPLETE extension.ts file with no placeholders.
```

## Alternative: Use the Ready-Made Extension

If generation fails or is incomplete, I can provide the complete working code. Just send your colleague:

1. The complete `vscode-copilot-bridge` folder (zipped)
2. Instructions: Extract, npm install, npm run compile, F5

## Troubleshooting Copilot Generation

### Issue: Copilot uses deprecated API

**Fix:** Ask Copilot:
```
Update the code to use the latest VS Code Chat API (vscode.lm.sendChatRequest) 
instead of deprecated APIs. Show me the corrected extension.ts.
```

### Issue: Missing Express server code

**Fix:** Ask Copilot:
```
The Express server setup is missing. Add:
1. Import express and body-parser
2. Create app = express()
3. Use body-parser.json() middleware
4. Add the POST /api/copilot/chat route
5. Start server with app.listen(3030)
Show complete code.
```

### Issue: Copilot API integration unclear

**Fix:** Ask Copilot:
```
Show me how to call GitHub Copilot from a VS Code extension using:
- vscode.lm.selectChatModels()
- model.sendRequest()
And convert the streaming response to a single string.
Provide complete working example.
```

## Quick Reference: Working Extension Code

If all else fails, here's the minimal working `extension.ts`:

```typescript
import * as vscode from 'vscode';
import * as express from 'express';
import * as bodyParser from 'body-parser';

export function activate(context: vscode.ExtensionContext) {
    const app = express();
    app.use(bodyParser.json());

    app.post('/api/copilot/chat', async (req, res) => {
        try {
            const { messages } = req.body;
            const lastMessage = messages[messages.length - 1];
            
            // Get Copilot model
            const [model] = await vscode.lm.selectChatModels({ family: 'gpt-4' });
            if (!model) {
                return res.status(503).json({ error: 'Copilot not available' });
            }

            // Send request
            const request = model.sendRequest(
                [new vscode.LanguageModelChatMessage('user', lastMessage.content)],
                {}
            );

            // Collect response
            let response = '';
            for await (const chunk of request.text) {
                response += chunk;
            }

            res.json({ response });
            
        } catch (error: any) {
            console.error('[COPILOT BRIDGE] Error:', error);
            res.status(500).json({ error: error.message });
        }
    });

    const server = app.listen(3030, () => {
        console.log('[COPILOT BRIDGE] Server running on http://localhost:3030');
    });

    context.subscriptions.push({
        dispose: () => server.close()
    });

    console.log('[COPILOT BRIDGE] Extension activated');
}

export function deactivate() {}
```

Your colleague can use this if Copilot-generated code doesn't work.

## Summary

**Tell your colleague:**

> "Open VS Code, open Copilot Chat, paste the prompt from PROMPT_FOR_COPILOT_BRIDGE.md, and let Copilot generate all the files. Then run `npm install`, `npm run compile`, and press F5. The bridge will be running on port 3030."
