# Port Configuration Guide

## Centralized Port Configuration

All port configurations are managed through the root `.env` file. To change ports, you only need to update **one file**.

### Configuration File: `.env`

```env
# Backend Configuration
API_PORT=8001
BACKEND_BASE_URL=http://localhost:8001

# Frontend Configuration
FRONTEND_PORT=5178
ALLOW_ORIGINS=http://localhost:5178
```

### How to Change Ports

**Example: Change backend to port 9000 and frontend to port 3000**

1. Edit `.env`:
   ```env
   API_PORT=9000
   BACKEND_BASE_URL=http://localhost:9000
   
   FRONTEND_PORT=3000
   ALLOW_ORIGINS=http://localhost:3000
   ```

2. Update `frontend/.env`:
   ```env
   VITE_API_BASE_URL=http://localhost:9000
   VITE_FRONTEND_PORT=3000
   ```

3. Restart services:
   ```bash
   start.bat
   ```

### Files That Auto-Update from .env

✅ Backend server (app/api/main.py) - reads `API_PORT`  
✅ Frontend dev server (vite.config.ts) - reads `VITE_FRONTEND_PORT`  
✅ CORS configuration (main.py) - reads `ALLOW_ORIGINS`  
✅ Frontend API client (client.ts) - reads `VITE_API_BASE_URL`  
✅ Startup script (start.bat) - reads ports for display

### No Need to Change These Files

The following files **automatically** use the environment variables:
- `app/api/main.py` - Backend server
- `frontend/vite.config.ts` - Frontend dev server  
- `frontend/src/api/client.ts` - API client
- `start.bat` - Startup script

### Legacy Hardcoded References (Documentation Only)

These files contain hardcoded port references **for documentation purposes only** and don't affect runtime:
- `QUICKSTART.md`
- `Installation.md`
- `docs/TEST_DATA_MAPPING_UI.md`

You can optionally update these markdown files to match your custom ports, but it's not required for the application to work.
