import json
import re
import requests
from crewai import Agent, Task, Crew, Process, LLM
from backend.config import settings
from backend.agents.prompts import (
    TASK1_DESCRIPTION, TASK2_DESCRIPTION,
    TASK3_DESCRIPTION, TASK_MORE_DESCRIPTION,
)


def parse_rate_limit_error(error_msg: str) -> dict | None:
    """
    Detect a Groq rate-limit error and extract the wait time.
    Returns None if the error is not a rate-limit error.
    """
    msg = str(error_msg)
    if "rate_limit_exceeded" not in msg and "Rate limit reached" not in msg:
        return None
    wait_match = re.search(
        r"Please try again in ([\d]+m[\d.]+s|[\d.]+s|[\d]+m[\d]+s)",
        msg,
    )
    wait = wait_match.group(1) if wait_match else "a few minutes"
    # Try to extract used/limit numbers for context
    limit_match = re.search(r"Limit ([\d,]+), Used ([\d,]+)", msg)
    limit = limit_match.group(1).replace(",", "") if limit_match else None
    used  = limit_match.group(2).replace(",", "") if limit_match else None
    return {
        "type":  "rate_limit",
        "wait":  wait,
        "limit": limit,
        "used":  used,
        "raw":   msg,
    }


def _build_llm(model: str, base_url: str, api_key: str,
               temperature: float = 0.0, max_tokens: int = 8000) -> LLM:
    return LLM(
        model=model,
        base_url=base_url,
        api_key=api_key,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def get_llm(ollama_url: str = "", ollama_model: str = "",
            groq_model_override: str = "") -> LLM:
    if ollama_url and ollama_model:
        return _build_llm(f"ollama/{ollama_model}", ollama_url, "ollama", 0.0, 8000)
    model = groq_model_override or settings.groq_model_main
    return _build_llm(model, settings.groq_base_url, settings.groq_api_key, 0.0, 8000)


def get_llm_reviewer(ollama_url: str = "", ollama_model: str = "",
                     groq_model_override: str = "") -> LLM:
    if ollama_url and ollama_model:
        return _build_llm(f"ollama/{ollama_model}", ollama_url, "ollama", 0.2, 3000)
    # Reviewer always uses the lightweight model unless overridden
    model = groq_model_override or settings.groq_model_reviewer
    return _build_llm(model, settings.groq_base_url, settings.groq_api_key, 0.2, 3000)


def parse_agent_json(raw: str) -> list:
    clean = raw.replace("```json", "").replace("```", "").strip()
    start = clean.find("[")
    if start == -1:
        return []
    json_text = clean[start:]
    try:
        return json.loads(json_text)
    except json.JSONDecodeError:
        pass
    objects, depth, obj_start, in_string, escape_next = [], 0, None, False, False
    for i, ch in enumerate(json_text):
        if escape_next:
            escape_next = False; continue
        if ch == chr(92) and in_string:
            escape_next = True; continue
        if ch == chr(34) and not escape_next:
            in_string = not in_string
        if in_string:
            continue
        if ch == "{":
            if depth == 0:
                obj_start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and obj_start is not None:
                try:
                    objects.append(json.loads(json_text[obj_start:i + 1]))
                except Exception:
                    pass
                obj_start = None
    return objects


def run_agent1(user_stories: str, llm: LLM) -> str:
    agent = Agent(
        role="QA Analyst & Business Analyst",
        goal="Perform static review, identify business gaps as JSON array, list technical concerns as JSON array, assess risks. JSON output only.",
        backstory="20 years Senior QA and BA expert with banking, security and market experience.",
        llm=llm, verbose=False,
    )
    task = Task(
        description=TASK1_DESCRIPTION.format(user_stories=user_stories),
        expected_output="Valid JSON array with identified_business_gaps and technical_concerns as JSON arrays.",
        agent=agent,
    )
    return Crew(agents=[agent], tasks=[task], process=Process.sequential, llm=llm, verbose=False).kickoff().raw


def run_agent2(report_raw: str, llm: LLM) -> str:
    agent = Agent(
        role="QA Test Case Designer",
        goal="Generate comprehensive enterprise-level QA test cases with SPECIFIC, OBSERVABLE expected results. JSON output only.",
        backstory="Senior Banking QA Engineer specialised in risk-based testing and regulatory compliance.",
        llm=llm, verbose=False,
    )
    task = Task(
        description=TASK2_DESCRIPTION.format(static_review_output=report_raw),
        expected_output="Valid JSON array — 30-50+ objects, all 9 keys, specific expected results.",
        agent=agent,
    )
    return Crew(agents=[agent], tasks=[task], process=Process.sequential, llm=llm, verbose=False).kickoff().raw


def run_agent3(report_raw: str, tc_raw: str, tc_list: list, llm_reviewer: LLM) -> str:
    tc_summaries = "\n".join(
        f"- {tc.get('Test Key', '')}: {tc.get('Summary', '')}"
        for tc in tc_list[:40]
    )
    agent = Agent(
        role="Senior QA Reviewer",
        goal="Independently review both agents, provide gap solutions and technical concern solutions. JSON output only.",
        backstory="Independent QA Director with 15 years of software quality governance experience.",
        llm=llm_reviewer, verbose=False,
    )
    task = Task(
        description=TASK3_DESCRIPTION.format(
            analysis_report=report_raw,
            tc_summaries=tc_summaries,
        ),
        expected_output="Valid JSON object with coverage_score, feedback arrays, solutions arrays.",
        agent=agent,
    )
    return Crew(agents=[agent], tasks=[task], process=Process.sequential, llm=llm_reviewer, verbose=False).kickoff().raw


def run_generate_more(user_story: str, report_raw: str,
                      existing_cases: list, count: int,
                      llm: LLM) -> list:
    existing_summaries = "\n".join(
        f"- {tc.get('Test Key', '')}: {tc.get('Summary', '')}"
        for tc in existing_cases
    )
    next_key = len(existing_cases) + 1
    agent = Agent(
        role="QA Test Case Extender",
        goal=f"Generate {count} additional non-duplicate test cases. JSON array only.",
        backstory="Senior QA Engineer focused on edge-case and boundary coverage in banking systems.",
        llm=llm, verbose=False,
    )
    task = Task(
        description=TASK_MORE_DESCRIPTION.format(
            user_story=user_story,
            analysis_report=report_raw,
            existing_summaries=existing_summaries,
            count=count,
            next_key=f"{next_key:03d}",
        ),
        expected_output="Valid JSON array only.",
        agent=agent,
    )
    result = Crew(agents=[agent], tasks=[task], process=Process.sequential, llm=llm, verbose=False).kickoff()
    return parse_agent_json(result.raw)


def chat_with_llm(messages: list, ollama_url: str = "", ollama_model: str = "") -> str:
    if ollama_url and ollama_model:
        base = ollama_url.rstrip("/")
        headers = {"Content-Type": "application/json"}
        payload = {"model": ollama_model, "messages": messages, "temperature": 0.7, "max_tokens": 2000}
        resp = requests.post(f"{base}/chat/completions", headers=headers, json=payload, timeout=120)
    else:
        headers = {
            "Authorization": f"Bearer {settings.groq_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": settings.groq_model_main,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 2000,
        }
        resp = requests.post(
            f"{settings.groq_base_url}/chat/completions",
            headers=headers, json=payload, timeout=60,
        )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]
