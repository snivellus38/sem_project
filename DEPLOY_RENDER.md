# Deploy AuraSense (Frontend + Backend Together)

This project is configured to run as a single Docker web service on Render:

- FastAPI backend serves APIs and WebSocket endpoints
- Built React frontend is served as static files by FastAPI

## 1. Push code to GitHub

From project root:

```powershell
git add .
git commit -m "Prepare full-stack Render deployment"
git push
```

## 2. Create Render service from Blueprint

1. Go to Render Dashboard.
2. Click **New +** -> **Blueprint**.
3. Connect your GitHub repo.
4. Render will detect `render.yaml`.
5. Confirm and create the service.

## 3. Wait for first deploy

Render builds from `Dockerfile` and starts:

```bash
uvicorn backend.main:app --host 0.0.0.0 --port ${PORT}
```

Health check path is:

```text
/api/status
```

## 4. Verify after deploy

- App root: `https://<your-service>.onrender.com/`
- API status: `https://<your-service>.onrender.com/api/status`
- WebSocket endpoint: `wss://<your-service>.onrender.com/ws/telemetry`

## Notes

- Frontend and backend share the same domain in production.
- Local development proxy is configured for backend on port `8000`.
- No extra Render environment variables are required for basic deployment.
