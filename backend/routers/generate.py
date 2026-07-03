import asyncio
import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from backend.agents.pipeline import (
    get_llm, get_llm_reviewer,
    run_agent1, run_agent2, run_agent3,
    run_generate_more, parse_agent_json,
    parse_rate_limit_error,
)

router = APIRouter()


class GenerateRequest(BaseModel):
    user_stories: str
    ollama_url: str = ""
    ollama_model_main: str = ""
    ollama_model_reviewer: str = ""
    groq_model: Optional[str] = ""


class GenerateMoreRequest(BaseModel):
    user_story: str
    report_raw: str
    existing_cases: list
    count: int = 10
    ollama_url: str = ""
    ollama_model_main: str = ""
    groq_model: Optional[str] = ""


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


def _error_sse(e: Exception) -> str:
    rl = parse_rate_limit_error(str(e))
    if rl:
        return _sse({
            "step": "rate_limit",
            "wait": rl["wait"],
            "limit": rl["limit"],
            "used": rl["used"],
            "msg": f"Groq daily token limit reached. Please wait {rl['wait']} or switch to a lighter model in Settings.",
        })
    return _sse({"step": "error", "msg": str(e)})


@router.post("/api/generate")
async def generate(req: GenerateRequest):
    async def stream():
        groq_override = req.groq_model or ""
        llm = get_llm(req.ollama_url, req.ollama_model_main, groq_override)
        llm_reviewer = get_llm_reviewer(req.ollama_url, req.ollama_model_reviewer, groq_override)

        yield _sse({"step": "agent1", "status": "running", "msg": "Running static review, risk analysis and gap identification…"})
        try:
            report_raw = await asyncio.to_thread(run_agent1, req.user_stories, llm)
        except Exception as e:
            yield _error_sse(e)
            return

        try:
            clean = report_raw.replace("```json", "").replace("```", "").strip()
            parsed = json.loads(clean)
            report_data = parsed[0] if isinstance(parsed, list) and parsed else {}
        except Exception:
            report_data = {}

        yield _sse({"step": "agent1", "status": "done", "report_data": report_data, "report_raw": report_raw})

        yield _sse({"step": "agent2", "status": "running", "msg": "Generating 30-50+ test cases with specific expected results…"})
        try:
            tc_raw = await asyncio.to_thread(run_agent2, report_raw, llm)
        except Exception as e:
            yield _error_sse(e)
            return

        tc_list = parse_agent_json(tc_raw)
        yield _sse({"step": "agent2", "status": "done", "tc_count": len(tc_list), "tc_list": tc_list})

        yield _sse({"step": "agent3", "status": "running", "msg": "Reviewing both agents and generating solutions…"})
        try:
            review_raw = await asyncio.to_thread(run_agent3, report_raw, tc_raw, tc_list, llm_reviewer)
        except Exception as e:
            yield _error_sse(e)
            return

        try:
            rev_clean = review_raw.replace("```json", "").replace("```", "").strip()
            obj_start = rev_clean.find("{")
            review_data = json.loads(rev_clean[obj_start:]) if obj_start != -1 else {}
        except Exception:
            review_data = {}

        yield _sse({"step": "agent3", "status": "done", "review_data": review_data})
        yield _sse({"step": "complete", "report_data": report_data, "review_data": review_data, "tc_list": tc_list, "tc_count": len(tc_list)})

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.post("/api/generate-more")
async def generate_more(req: GenerateMoreRequest):
    groq_override = req.groq_model or ""
    llm = get_llm(req.ollama_url, req.ollama_model_main, groq_override)
    try:
        new_cases = await asyncio.to_thread(
            run_generate_more,
            req.user_story, req.report_raw,
            req.existing_cases, req.count, llm,
        )
        return {"success": True, "new_cases": new_cases, "count": len(new_cases)}
    except Exception as e:
        rl = parse_rate_limit_error(str(e))
        if rl:
            return {"success": False, "rate_limit": True, "wait": rl["wait"],
                    "error": f"Rate limit reached. Wait {rl['wait']}.", "new_cases": []}
        return {"success": False, "error": str(e), "new_cases": []}
