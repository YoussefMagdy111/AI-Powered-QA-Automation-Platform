"""
main.py — QA Ninjas: Agentic AI Test Suite Generator
FastAPI entry point
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from backend.db import init_db
from backend.routers.auth import router as auth_router
from backend.routers.generate import router as generate_router
from backend.routers.chat import router as chat_router
from backend.routers.download import router as download_router
from backend.routers.history import router as history_router
from backend.routers.export_pdf import router as pdf_router
from backend.routers.export_jira import router as jira_router
from backend.routers.figma import router as figma_router

app = FastAPI(
    title="QA Ninjas",
    description="Agentic AI Test Suite Generator — Three-Agent Pipeline",
    version="2.3.0",
)

init_db()

app.include_router(auth_router)
app.include_router(generate_router)
app.include_router(chat_router)
app.include_router(download_router)
app.include_router(history_router)
app.include_router(pdf_router)
app.include_router(jira_router)
app.include_router(figma_router)

FRONTEND_DIR = Path(__file__).parent / "frontend"


@app.get("/")
async def serve_index():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/health")
async def health():
    return {"status": "ok", "app": "QA Ninjas v2.3"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("APP_PORT", 5000))
    host = os.getenv("APP_HOST", "0.0.0.0")
    uvicorn.run("main:app", host=host, port=port, reload=True)
