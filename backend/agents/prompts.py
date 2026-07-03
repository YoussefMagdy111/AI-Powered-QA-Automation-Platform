TASK1_DESCRIPTION = """
Review and analyze the following user stories:
{user_stories}

OUTPUT MUST BE VALID JSON matching this exact structure:
[
  {{
    "user_story_id": "US-01",
    "user_story_title": "Short descriptive title",
    "static_review_analysis": "Detailed static review covering clarity, completeness, assumptions, ambiguities, and missing acceptance criteria.",
    "business_risk_level": "High",
    "technical_risk_level": "Medium",
    "overall_risk_level": "High",
    "identified_business_gaps": [
      "Gap 1 — describe the missing business rule or edge case in one clear sentence",
      "Gap 2 — describe the unclear stakeholder expectation or regulatory gap",
      "Gap 3 — add as many distinct gaps as identified, minimum 3"
    ],
    "technical_concerns": [
      "Concern 1 — describe the concurrency / race-condition risk in one sentence",
      "Concern 2 — describe the security or authentication gap",
      "Concern 3 — describe the performance, dependency or API risk; minimum 3 items"
    ],
    "reviewer_opinion": "Professional reviewer judgment on readiness for development.",
    "manager_summary": "2-3 sentence summary of key risks, gaps and recommended actions for management."
  }}
]

RULES:
- identified_business_gaps  MUST be a JSON array of strings
- technical_concerns         MUST be a JSON array of strings
- business_risk_level, technical_risk_level, overall_risk_level MUST be exactly one of: Low | Medium | High
- manager_summary MUST always be present and non-empty
- Return ONLY the JSON array — no markdown fences, no prose
"""

TASK2_DESCRIPTION = """
Generate a COMPREHENSIVE, enterprise-grade test suite with 30-50+ test cases.

EXCEL HEADERS (FIXED):
Test Key | Summary | Type | Component | Description | Action | Data | Expected Result | Release

- Every JSON object MUST contain ALL 9 keys
- Array length MUST be 30-50 objects minimum

ACTION COLUMN RULES:
- Action = single string, steps separated by \\n
- Each step starts with an imperative verb (Login, Open, Navigate, Click, Enter, Save, Verify, Select, Submit, Clear, Assert)
- Every Action MUST end with Verify or Click Save

DATA COLUMN RULES:
- Data = the exact test input value(s) used in this test case
- Use pipe | to provide one value per Action step in step order
- NEVER leave Data empty — if no data is needed write "N/A"

EXPECTED RESULT RULES:
- Use pipe | to separate one result per Action step in the SAME ORDER as the steps
- The number of pipe-separated entries MUST equal the number of Action steps exactly
- EVERY result entry MUST be SPECIFIC and OBSERVABLE
- NEVER use "As expected" or "Works correctly"

TEST COVERAGE (MANDATORY):
- Positive scenarios: minimum 5
- Validation rules: minimum 1 per rule
- Boundary conditions: minimum 2 per boundary
- Negative scenarios: minimum 5
- Error message verification: minimum 1 per unique error
- Save blocking behavior: minimum 1 per invalid state
- Identified risks: minimum 2 per risk
- Business gaps: minimum 1 per gap
- Edge cases: minimum 3
- Workflow variations: minimum 3

SUMMARY FORMAT:
UI:  [User Story Name] - Validate that [the test case]
API: API_[Module]_[Method]_[Story]_Check response when [description]

OUTPUT FORMAT:
- Return ONLY a valid JSON array [ ... ]
- NO markdown fences, NO prose, NO comments, NO trailing commas

INPUT:
{static_review_output}
"""

TASK3_DESCRIPTION = """
You are a Senior QA Reviewer. Review both Agent 1's analysis and Agent 2's test cases.

AGENT 1 — ANALYSIS REPORT:
{analysis_report}

AGENT 2 — TEST CASE SUMMARIES:
{tc_summaries}

YOUR OUTPUT — valid JSON object only, no markdown, no prose:
{{
  "coverage_score": 82,
  "agent1_feedback": [
    "Feedback point about Agent 1 analysis",
    "Another specific feedback point"
  ],
  "agent2_feedback": [
    "Feedback on test case quality",
    "Coverage gap"
  ],
  "business_gap_solutions": [
    "Solution for Gap 1: actionable recommendation",
    "Solution for Gap 2: specific fix"
  ],
  "technical_concern_solutions": [
    "Solution for Concern 1: concrete technical fix",
    "Solution for Concern 2: specific mitigation"
  ],
  "reviewer_summary": "2-3 sentence executive summary of overall quality and top recommendations."
}}

RULES:
- ALL four array fields MUST be JSON arrays of strings
- business_gap_solutions: one entry per gap from Agent 1 in same order
- technical_concern_solutions: one entry per concern from Agent 1 in same order
- coverage_score: integer 0-100
"""

TASK_MORE_DESCRIPTION = """
You are a QA Test Case Designer. Additional test cases are needed.

USER STORY:
{user_story}

ANALYSIS REPORT (from Agent 1):
{analysis_report}

ALREADY GENERATED TEST CASES — DO NOT DUPLICATE:
{existing_summaries}

YOUR TASK:
- Generate {count} NEW test cases NOT already in the list above
- Focus on: edge cases, boundary conditions, error scenarios, workflow variations
- Use the EXACT SAME 9-key schema: Test Key, Summary, Type, Component, Description, Action, Data, Expected Result, Release
- Start Test Key numbering from TC-{next_key}
- Follow ALL Action formatting rules (\\n steps, imperative verbs, ends with Verify/Save)
- EXPECTED RESULT must be specific and observable
- Return ONLY a valid JSON array [ ... ] — no markdown, no prose
"""
