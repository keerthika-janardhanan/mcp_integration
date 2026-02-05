# Step-by-Step: Run VS Code Copilot Bridge

## Step 1: Close Mock Server
Close the cmd window running `node copilot-bridge-server.js`

## Step 2: Open Extension Folder
1. Open NEW VS Code window
2. File → Open Folder
3. Navigate to: `C:\Users\keerthee\gen_ai\copilot_integration\vscode-copilot-bridge`
4. Click "Select Folder"

## Step 3: Open Run & Debug Panel
- Click the Run icon in left sidebar (triangle with bug)
- OR press: Ctrl+Shift+D

## Step 4: Select Configuration
In the dropdown at top, select: **"Run Extension"**

## Step 5: Start Debugging
Click the green play button (▶) next to the dropdown
- OR press F5

## Step 6: Wait for New Window
A NEW VS Code window will open (Extension Development Host)

## Step 7: Check Debug Console (in ORIGINAL window)
1. View → Debug Console
2. Look for:
```
[COPILOT BRIDGE] Extension activated
[COPILOT BRIDGE] Server running on http://localhost:3030
```

## Step 8: Test
Go to your UI and trigger any LLM action. Watch backend console for:
```
[COPILOT] Sending request to http://localhost:3030/api/copilot/chat
[COPILOT] ✓ Response received (status: 200)
```

## Done!
Keep both VS Code windows open while using your app.
