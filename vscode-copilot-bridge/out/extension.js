"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = require("vscode");
const express = require("express");
const bodyParser = require("body-parser");
let server;
function activate(context) {
    console.log('[COPILOT BRIDGE] Extension activated');
    const app = express();
    app.use(bodyParser.json());
    app.post('/api/copilot/chat', async (req, res) => {
        const timestamp = new Date().toISOString();
        console.log(`[${timestamp}] ===== COPILOT REQUEST START =====`);
        console.log(`[${timestamp}] REQUEST BODY:`, JSON.stringify(req.body, null, 2));
        try {
            const { messages } = req.body;
            const prompt = messages[0].content;
            console.log(`[${timestamp}] EXTRACTED PROMPT:`, prompt);
            // List all available models for debugging
            const allModels = await vscode.lm.selectChatModels();
            console.log(`[${timestamp}] Available models:`, allModels.map(m => `${m.id} (${m.family})`).join(', '));
            // Try Claude Sonnet 4.5 first (preferred model) - match by ID
            let models = allModels.filter(m => m.id === 'claude-sonnet-4.5' || m.family === 'claude-sonnet-4.5');
            if (!models || models.length === 0) {
                console.log(`[${timestamp}] Claude Sonnet 4.5 not found, trying claude-sonnet-4...`);
                models = allModels.filter(m => m.id === 'claude-sonnet-4' || m.family === 'claude-sonnet-4');
            }
            if (!models || models.length === 0) {
                console.log(`[${timestamp}] Claude Sonnet not found, trying gpt-5...`);
                models = await vscode.lm.selectChatModels({ vendor: 'copilot', family: 'gpt-5' });
            }
            if (!models || models.length === 0) {
                console.log(`[${timestamp}] gpt-5 not found, trying gpt-3.5-turbo...`);
                models = await vscode.lm.selectChatModels({ vendor: 'copilot', family: 'gpt-3.5-turbo' });
            }
            if (!models || models.length === 0) {
                console.log(`[${timestamp}] No copilot models found, using first available model...`);
                if (allModels.length > 0) {
                    models = [allModels[0]];
                }
                else {
                    return res.status(503).json({ error: 'No language models available. Ensure GitHub Copilot or another AI assistant is installed and authenticated.' });
                }
            }
            const model = models[0];
            console.log(`[${timestamp}] Using model: ${model.id} (vendor: ${model.vendor}, family: ${model.family})`);
            const chatMessages = [vscode.LanguageModelChatMessage.User(prompt)];
            const response = await model.sendRequest(chatMessages, {}, new vscode.CancellationTokenSource().token);
            let fullResponse = '';
            for await (const chunk of response.text) {
                fullResponse += chunk;
            }
            console.log(`[${timestamp}] ===== MODEL RESPONSE =====`);
            console.log(`[${timestamp}] FULL RESPONSE:`, fullResponse);
            console.log(`[${timestamp}] ===== SENDING RESPONSE =====`);
            const responsePayload = { content: fullResponse };
            console.log(`[${timestamp}] RESPONSE PAYLOAD:`, JSON.stringify(responsePayload, null, 2));
            console.log(`[${timestamp}] SUCCESS: Response length: ${fullResponse.length} chars`);
            res.json(responsePayload);
        }
        catch (error) {
            console.log(`[${timestamp}] ERROR: ${error.message}`);
            console.log(`[${timestamp}] ERROR Stack:`, error.stack);
            res.status(500).json({ error: error.message });
        }
    });
    server = app.listen(3030, () => {
        console.log('[COPILOT BRIDGE] Server running on http://localhost:3030');
        vscode.window.showInformationMessage('Copilot Bridge: Server started on port 3030');
    });
    context.subscriptions.push({
        dispose: () => server?.close()
    });
}
function deactivate() {
    console.log('[COPILOT BRIDGE] Extension deactivated');
    server?.close();
}
//# sourceMappingURL=extension.js.map