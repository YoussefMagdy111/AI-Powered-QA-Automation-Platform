"""
backend/routers/figma.py — Figma Design-to-Test Cases & Screenshot Review
"""
import json
import re
import requests
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from backend.config import settings

router = APIRouter()

GROQ_API    = "https://api.groq.com/openai/v1/chat/completions"
TEXT_MODEL  = "llama-3.3-70b-versatile"
VISION_MODEL = "llama-3.2-11b-vision-preview"


def _groq_headers() -> dict:
    return {
        "Authorization": f"Bearer {settings.groq_api_key}",
        "Content-Type":  "application/json",
    }


def _extract_file_key(figma_url: str) -> Optional[str]:
    m = re.search(r"figma\.com/(?:file|design)/([A-Za-z0-9]+)", figma_url)
    return m.group(1) if m else None


def _parse_json_array(raw: str) -> list:
    clean = raw.strip()
    start = clean.find("[")
    end   = clean.rfind("]") + 1
    if start != -1 and end > start:
        try:
            return json.loads(clean[start:end])
        except Exception:
            pass
    return []


def _parse_json_obj(raw: str) -> dict:
    clean = raw.strip()
    start = clean.find("{")
    end   = clean.rfind("}") + 1
    if start != -1 and end > start:
        try:
            return json.loads(clean[start:end])
        except Exception:
            pass
    return {"raw_analysis": raw}


class FigmaAnalyzeRequest(BaseModel):
    figma_url:   str
    figma_token: str
    user_story:  str
    groq_model:  Optional[str] = ""


class FigmaScreenshotRequest(BaseModel):
    image_base64: str
    image_name:   Optional[str] = "Figma Frame"
    user_story:   Optional[str] = ""
    groq_model:   Optional[str] = ""


def _walk_nodes(node, frames: list, components: list, depth: int = 0):
    if depth > 6:
        return
    node_type = node.get("type", "")
    name = node.get("name", "")
    children = node.get("children", [])
    if node_type in ("FRAME", "COMPONENT", "INSTANCE", "SECTION"):
        entry = {
            "type": node_type,
            "name": name,
            "children_count": len(children),
        }
        child_names = [c.get("name", "") for c in children[:12] if c.get("name")]
        if child_names:
            entry["child_elements"] = child_names
        if node_type in ("FRAME", "SECTION"):
            frames.append(entry)
        else:
            components.append(entry)
    for child in children:
        _walk_nodes(child, frames, components, depth + 1)


@router.post("/api/figma/analyze")
def analyze_figma(req: FigmaAnalyzeRequest):
    file_key = _extract_file_key(req.figma_url)
    if not file_key:
        return {
            "success": False,
            "error": "Invalid Figma URL. Expected format: https://www.figma.com/file/<key>/... or https://www.figma.com/design/<key>/..."
        }

    figma_headers = {"X-Figma-Token": req.figma_token}
    try:
        r = requests.get(
            f"https://api.figma.com/v1/files/{file_key}",
            headers=figma_headers,
            timeout=30,
        )
        if r.status_code == 403:
            return {"success": False, "error": "Invalid Figma API token or you don't have access to this file."}
        if r.status_code == 404:
            return {"success": False, "error": "Figma file not found. Check the URL."}
        if r.status_code != 200:
            return {"success": False, "error": f"Figma API returned HTTP {r.status_code}."}
        figma_data = r.json()
    except Exception as e:
        return {"success": False, "error": f"Failed to reach Figma API: {str(e)}"}

    doc       = figma_data.get("document", {})
    file_name = figma_data.get("name", "Figma File")
    frames: list    = []
    components: list = []
    _walk_nodes(doc, frames, components)

    frame_lines = []
    for f in frames[:25]:
        line = f"  • {f['type']}: {f['name']} ({f['children_count']} children)"
        if f.get("child_elements"):
            line += f"\n    Elements: {', '.join(f['child_elements'][:10])}"
        frame_lines.append(line)
    comp_lines = [f"  • {c['name']}" for c in components[:20]]

    design_context = (
        f"Figma File: {file_name}\n\n"
        f"SCREENS/FRAMES ({len(frames)} total, showing up to 25):\n"
        + ("\n".join(frame_lines) or "  None found.")
        + f"\n\nCOMPONENTS ({len(components)} total, showing up to 20):\n"
        + ("\n".join(comp_lines) or "  None found.")
    )

    model = req.groq_model or TEXT_MODEL
    system_msg = (
        "You are a senior QA engineer specialising in UI/UX testing. "
        "Given a Figma design structure and a user story, generate a comprehensive set of UI/UX test cases.\n"
        "Focus on: visual states, user interactions, accessibility, responsive behaviour, "
        "error states, empty states, loading states, form validation, navigation flows, and design consistency.\n\n"
        "Return ONLY a JSON array. Each element must be an object with exactly these fields:\n"
        "Test Key, Summary, Category, Priority, Test Steps, Expected Result, Risk Level.\n\n"
        "Category values: UI/Visual | Accessibility | Interaction | Navigation | State Management | Validation"
    )
    user_msg = (
        f"USER STORY:\n{req.user_story}\n\n"
        f"FIGMA DESIGN STRUCTURE:\n{design_context}\n\n"
        "Generate 15–25 detailed UI/UX test cases that cover all critical design elements, "
        "user flows, accessibility requirements, and edge cases visible from the Figma structure.\n"
        "Return ONLY the JSON array."
    )

    try:
        resp = requests.post(GROQ_API, headers=_groq_headers(), json={
            "model":       model,
            "messages":    [
                {"role": "system", "content": system_msg},
                {"role": "user",   "content": user_msg},
            ],
            "temperature": 0.3,
            "max_tokens":  4000,
        }, timeout=90)
        if resp.status_code != 200:
            return {"success": False, "error": f"LLM error ({resp.status_code}): {resp.text[:300]}"}
        raw     = resp.json()["choices"][0]["message"]["content"]
        tc_list = _parse_json_array(raw)
        return {
            "success":          True,
            "file_name":        file_name,
            "frames_count":     len(frames),
            "components_count": len(components),
            "tc_list":          tc_list,
            "tc_count":         len(tc_list),
            "design_summary":   design_context[:900],
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/api/figma/review-screenshot")
def review_screenshot(req: FigmaScreenshotRequest):
    model = req.groq_model or VISION_MODEL
    image_url = f"data:image/png;base64,{req.image_base64}"

    system_msg = (
        "You are a senior UX/QA engineer specialising in design review and accessibility auditing. "
        "Analyse the provided UI screenshot and identify all issues.\n\n"
        "Return ONLY a JSON object with exactly these fields:\n"
        "{\n"
        '  "overall_score": 0-100,\n'
        '  "missing_states": ["list of missing UI states e.g. loading, error, empty"],\n'
        '  "accessibility_issues": ["WCAG violations, contrast, missing alt text, focus, etc."],\n'
        '  "label_issues": ["missing labels, unclear CTAs, inconsistent naming"],\n'
        '  "ux_issues": ["confusing flows, poor hierarchy, dead zones"],\n'
        '  "positive_aspects": ["what is done well"],\n'
        '  "recommendations": ["prioritised action items"]\n'
        "}"
    )
    user_content = [
        {
            "type": "text",
            "text": (
                f"Review this UI screenshot{(' for the user story: ' + req.user_story) if req.user_story else ''}. "
                "Identify UX issues, missing states, accessibility violations, and missing labels. "
                "Return only the JSON object."
            ),
        },
        {"type": "image_url", "image_url": {"url": image_url}},
    ]

    try:
        resp = requests.post(GROQ_API, headers=_groq_headers(), json={
            "model":       model,
            "messages":    [
                {"role": "system", "content": system_msg},
                {"role": "user",   "content": user_content},
            ],
            "temperature": 0.3,
            "max_tokens":  2000,
        }, timeout=90)
        if resp.status_code != 200:
            return {"success": False, "error": f"Vision model error ({resp.status_code}): {resp.text[:300]}"}
        raw    = resp.json()["choices"][0]["message"]["content"]
        review = _parse_json_obj(raw)
        return {"success": True, "image_name": req.image_name, "review": review}
    except Exception as e:
        return {"success": False, "error": str(e)}
