import asyncio
from fastapi import APIRouter
from pydantic import BaseModel
from backend.agents.pipeline import chat_with_llm

router = APIRouter()


class ChatRequest(BaseModel):
    messages: list
    ollama_url: str = ""
    ollama_model: str = ""


@router.post("/api/chat")
async def chat(req: ChatRequest):
    try:
        reply = await asyncio.to_thread(
            chat_with_llm,
            req.messages, req.ollama_url, req.ollama_model,
        )
        return {"success": True, "reply": reply}
    except Exception as e:
        return {"success": False, "error": str(e), "reply": ""}
