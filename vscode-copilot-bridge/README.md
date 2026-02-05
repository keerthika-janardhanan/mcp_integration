# Copilot Bridge Extension

VS Code extension that exposes GitHub Copilot Chat API via HTTP server.

## Installation

1. Install dependencies:
```bash
npm install
```

2. Compile TypeScript:
```bash
npm run compile
```

3. Launch extension:
- Press F5 in VS Code
- Or run: `code --extensionDevelopmentPath=.`

## Usage

The extension automatically starts an HTTP server on port 3030 when VS Code launches.

### API Endpoint

**POST** `http://localhost:3030/api/copilot/chat`

Request:
```json
{
  "messages": [
    {"role": "user", "content": "Your prompt here"}
  ],
  "temperature": 0.2
}
```

Response:
```json
{
  "content": "Copilot's response"
}
```

## Requirements

- VS Code 1.85.0+
- GitHub Copilot subscription
- GitHub Copilot extension installed

## Port Configuration

Default port: 3030

To change, modify `extension.ts`:
```typescript
server = app.listen(3030, () => { ... });
```
