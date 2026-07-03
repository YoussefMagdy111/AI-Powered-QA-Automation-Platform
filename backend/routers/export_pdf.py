"""
backend/routers/export_pdf.py — Professional PDF report generation
"""
import json
from io import BytesIO
from datetime import datetime
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether,
)
from reportlab.lib.enums import TA_CENTER
from backend.db import get_conn

router = APIRouter()

NAVY   = colors.HexColor('#0d1526')
PURPLE = colors.HexColor('#6c63ff')
TEAL   = colors.HexColor('#00d4aa')
ORANGE = colors.HexColor('#f5a623')
RED    = colors.HexColor('#ff4757')
GRAY   = colors.HexColor('#8892a4')
LGRAY  = colors.HexColor('#e2e8f0')
WHITE  = colors.white
BLACK  = colors.HexColor('#1a1a2e')
LP     = colors.HexColor('#f0efff')
LT     = colors.HexColor('#e6fff9')
LR     = colors.HexColor('#fff0f1')
LO     = colors.HexColor('#fff8ed')
LG     = colors.HexColor('#f8f8fb')


def _esc(s):
    return str(s or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def _h(text, size=13, color=BLACK, space_after=6):
    return Paragraph(text, ParagraphStyle(
        'h', fontSize=size, textColor=color,
        fontName='Helvetica-Bold', spaceAfter=space_after, leading=size * 1.35,
    ))


def _p(text, size=9, color=BLACK, space_after=4, leading=None):
    return Paragraph(text, ParagraphStyle(
        'p', fontSize=size, textColor=color, fontName='Helvetica',
        spaceAfter=space_after, leading=leading or size * 1.5,
    ))


def _sp(n=8):
    return Spacer(1, n)


def _hr():
    return HRFlowable(width='100%', thickness=0.5, color=LGRAY, spaceAfter=6)


def _cell(text, **kw):
    defaults = dict(fontSize=8, textColor=BLACK, fontName='Helvetica', leading=11)
    defaults.update(kw)
    return Paragraph(text, ParagraphStyle('c', **defaults))


def _build_pdf(user_story: str, report_data: dict, review_data: dict,
               tc_list: list, label: str, run_date: str) -> BytesIO:
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=1.8 * cm, rightMargin=1.8 * cm,
        topMargin=1.8 * cm, bottomMargin=1.8 * cm,
        title="QA Ninjas Test Suite Report",
    )

    W = 16.4 * cm
    story = []
    rd = report_data or {}
    rv = review_data or {}
    tcs = tc_list or []
    now = run_date or datetime.now().strftime('%B %d, %Y  %H:%M')
    lbl = label or 'Untitled Run'

    # ── Cover banner ──────────────────────────────────────────────────
    banner_data = [[
        Paragraph('<font color="white"><b>🧪  QA Ninjas</b></font>',
                  ParagraphStyle('', fontSize=20, textColor=WHITE,
                                 fontName='Helvetica-Bold', leading=26)),
        Paragraph('<font color="#9aa8c0">Agentic AI Test Suite Generator<br/>'
                  'Three-Agent Pipeline · CrewAI + Groq</font>',
                  ParagraphStyle('', fontSize=8.5, textColor=colors.HexColor('#9aa8c0'),
                                 fontName='Helvetica', leading=13)),
    ]]
    banner = Table(banner_data, colWidths=[8 * cm, None])
    banner.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), NAVY),
        ('VALIGN',     (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING',    (0, 0), (-1, -1), 16),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 16),
        ('LEFTPADDING',   (0, 0), (-1, -1), 18),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 12),
        ('ROUNDEDCORNERS', [8]),
    ]))
    story.append(banner)
    story.append(_sp(12))

    # Run meta
    meta_rows = [
        ['Report Label', lbl],
        ['Generated',    now],
        ['Total Test Cases', str(len(tcs))],
        ['Coverage Score',
         (str(rv.get('coverage_score', '—')) + '%') if rv.get('coverage_score') is not None else '—'],
        ['Overall Risk',
         (rd.get('overall_risk_level') or '—').title()],
    ]
    meta_tbl = Table(meta_rows, colWidths=[3.8 * cm, W - 3.8 * cm])
    meta_tbl.setStyle(TableStyle([
        ('FONTNAME',    (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE',    (0, 0), (-1, -1), 8.5),
        ('TEXTCOLOR',   (0, 0), (0, -1), PURPLE),
        ('TEXTCOLOR',   (1, 0), (1, -1), BLACK),
        ('ROWBACKGROUNDS', (0, 0), (-1, -1), [LP, WHITE]),
        ('TOPPADDING',    (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING',   (0, 0), (-1, -1), 8),
        ('GRID',        (0, 0), (-1, -1), 0.3, LGRAY),
    ]))
    story.append(meta_tbl)
    story.append(_sp(10))

    # Metrics row
    m_labels = ['Business Risk', 'Technical Risk', 'Overall Risk', 'Test Cases', 'Coverage %']

    def _risk_color(r):
        r = (r or '').lower()
        return RED if r == 'high' else ORANGE if r == 'medium' else TEAL if r == 'low' else GRAY

    m_vals = [
        rd.get('business_risk_level', '—').title() if rd.get('business_risk_level') else '—',
        rd.get('technical_risk_level', '—').title() if rd.get('technical_risk_level') else '—',
        rd.get('overall_risk_level', '—').title() if rd.get('overall_risk_level') else '—',
        str(len(tcs)),
        (str(rv.get('coverage_score')) + '%') if rv.get('coverage_score') is not None else '—',
    ]
    risk_keys = ['business_risk_level', 'technical_risk_level', 'overall_risk_level', None, None]
    cw = W / 5
    hdr_row = [Paragraph(f'<font color="white"><b>{l}</b></font>',
                         ParagraphStyle('', fontSize=7.5, fontName='Helvetica-Bold',
                                        alignment=TA_CENTER, leading=10))
               for l in m_labels]
    val_row = [Paragraph(f'<b>{v}</b>',
                         ParagraphStyle('', fontSize=11, fontName='Helvetica-Bold',
                                        alignment=TA_CENTER,
                                        textColor=(_risk_color(rd.get(risk_keys[i])) if i < 3
                                                   else (TEAL if i == 4 else BLACK))))
               for i, v in enumerate(m_vals)]
    m_tbl = Table([hdr_row, val_row], colWidths=[cw] * 5)
    m_tbl.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, 0), NAVY),
        ('BACKGROUND',    (0, 1), (-1, 1), LP),
        ('TOPPADDING',    (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ('GRID',          (0, 0), (-1, -1), 0.3, LGRAY),
    ]))
    story.append(m_tbl)
    story.append(_sp(10))

    # Executive summary
    if rd.get('manager_summary'):
        ms = [[Paragraph(
            f'<b>📌 Executive Summary:</b>  {_esc(rd["manager_summary"])}',
            ParagraphStyle('', fontSize=8.5, fontName='Helvetica', leading=13, textColor=BLACK),
        )]]
        mst = Table(ms, colWidths=[W])
        mst.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), LP),
            ('LEFTPADDING',  (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING',   (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING',(0, 0), (-1, -1), 8),
            ('LINEAFTER',    (0, 0), (0, -1), 3, PURPLE),
            ('GRID',         (0, 0), (-1, -1), 0, WHITE),
        ]))
        story.append(mst)
        story.append(_sp(10))

    # ── Section 1: User Story ──────────────────────────────────────
    story.append(KeepTogether([
        _h('1.  User Story', 12, PURPLE),
        _hr(),
    ] + [_p(_esc(line), size=8.5) for line in user_story.strip().split('\n') if line.strip()]))
    story.append(_sp(12))

    # ── Section 2: Analysis ───────────────────────────────────────
    story.append(_h('2.  QA Analysis Report', 12, PURPLE))
    story.append(_hr())

    def _list_tbl(items, bg, alt_bg):
        rows = [[Paragraph(f'<b>{i+1}.</b>  {_esc(str(item))}',
                           ParagraphStyle('', fontSize=8, fontName='Helvetica', leading=12))]
                for i, item in enumerate(items)]
        t = Table(rows, colWidths=[W])
        t.setStyle(TableStyle([
            ('ROWBACKGROUNDS', (0, 0), (-1, -1), [bg, alt_bg]),
            ('LEFTPADDING',  (0, 0), (-1, -1), 8), ('RIGHTPADDING',  (0, 0), (-1, -1), 8),
            ('TOPPADDING',   (0, 0), (-1, -1), 5), ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('GRID', (0, 0), (-1, -1), 0.3, LGRAY),
        ]))
        return t

    if rd.get('static_review_analysis'):
        review_txt = _esc(str(rd['static_review_analysis'])[:1800])
        story.append(_h('Static Review', 9.5, NAVY, space_after=4))
        rt = Table([[Paragraph(review_txt.replace('\n', '<br/>'),
                               ParagraphStyle('', fontSize=8, fontName='Helvetica', leading=12))]], colWidths=[W])
        rt.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), LG),
            ('LEFTPADDING',  (0, 0), (-1, -1), 8), ('RIGHTPADDING',  (0, 0), (-1, -1), 8),
            ('TOPPADDING',   (0, 0), (-1, -1), 6), ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.3, LGRAY),
        ]))
        story.append(rt)
        story.append(_sp(8))

    if rd.get('identified_business_gaps'):
        story.append(_h('⚠️  Business Gaps', 9.5, RED, space_after=4))
        story.append(_list_tbl(rd['identified_business_gaps'], LR, WHITE))
        story.append(_sp(8))

    if rd.get('technical_concerns'):
        story.append(_h('🔧  Technical Concerns', 9.5, ORANGE, space_after=4))
        story.append(_list_tbl(rd['technical_concerns'], LO, WHITE))
        story.append(_sp(8))

    # ── Section 3: Test Cases ──────────────────────────────────────
    story.append(PageBreak())
    story.append(_h('3.  Test Cases', 12, PURPLE))
    story.append(_hr())

    if tcs:
        pri_colors = {
            'critical': '#cc0000', 'high': '#e03040',
            'medium':   '#d4820a', 'low':  '#009977',
        }
        hdr = [_cell(t, fontName='Helvetica-Bold', textColor=WHITE, alignment=TA_CENTER)
               for t in ['#', 'Test Key', 'Summary', 'Priority', 'Risk', 'Expected Result']]
        col_w = [0.6*cm, 1.9*cm, 4.8*cm, 1.5*cm, 1.5*cm, 6.1*cm]
        tc_rows = [hdr]
        for i, tc in enumerate(tcs):
            pri = str(tc.get('Priority') or tc.get('priority') or 'Medium')
            pc  = pri_colors.get(pri.lower(), '#333333')
            key = _esc(tc.get('Test Key') or tc.get('test_key') or f'TC-{i+1:03d}')
            tc_rows.append([
                _cell(str(i+1), textColor=GRAY, alignment=TA_CENTER),
                _cell(f'<font color="#6c63ff"><b>{key}</b></font>', alignment=TA_CENTER),
                _cell(_esc(str(tc.get('Summary') or '')[:120])),
                _cell(f'<font color="{pc}"><b>{pri}</b></font>', alignment=TA_CENTER),
                _cell(_esc(str(tc.get('Risk Level') or tc.get('risk_level') or tc.get('Risk') or '')),
                      textColor=GRAY, alignment=TA_CENTER),
                _cell(_esc(str(tc.get('Expected Result') or tc.get('expected_result') or '')[:160])),
            ])
        tc_tbl = Table(tc_rows, colWidths=col_w, repeatRows=1)
        tc_tbl.setStyle(TableStyle([
            ('BACKGROUND',     (0, 0), (-1, 0), NAVY),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [LP, WHITE]),
            ('TOPPADDING',    (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING',   (0, 0), (-1, -1), 4),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 4),
            ('GRID',          (0, 0), (-1, -1), 0.3, LGRAY),
            ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(tc_tbl)
    else:
        story.append(_p('No test cases available.', color=GRAY))
    story.append(_sp(12))

    # ── Section 4: Reviewer Findings ──────────────────────────────
    story.append(PageBreak())
    story.append(_h('4.  Agent 3 — Reviewer Findings', 12, PURPLE))
    story.append(_hr())

    if rv.get('reviewer_summary'):
        rs = [[Paragraph(
            f'<b>🔎  Reviewer Summary:</b>  {_esc(rv["reviewer_summary"])}',
            ParagraphStyle('', fontSize=8.5, fontName='Helvetica', leading=13),
        )]]
        rst = Table(rs, colWidths=[W])
        rst.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (-1, -1), LT),
            ('LEFTPADDING',   (0, 0), (-1, -1), 10),
            ('TOPPADDING',    (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID',          (0, 0), (-1, -1), 0.3, LGRAY),
        ]))
        story.append(rst)
        story.append(_sp(8))

    def _rev_section(title, items, bg):
        if not items:
            return
        story.append(_h(title, 9.5, NAVY, space_after=4))
        story.append(_list_tbl(items, bg, WHITE))
        story.append(_sp(8))

    _rev_section('Agent 1 Feedback',            rv.get('agent1_feedback', []),             LP)
    _rev_section('Agent 2 Feedback',            rv.get('agent2_feedback', []),             LP)
    _rev_section('✅  Business Gap Solutions',   rv.get('business_gap_solutions', []),      LT)
    _rev_section('🔧  Technical Solutions',      rv.get('technical_concern_solutions', []), LO)

    # Footer
    story.append(_sp(16))
    ft_data = [[Paragraph(
        f'<font color="#8892a4">Generated by QA Ninjas · {now} · '
        f'Confidential — For QA &amp; Stakeholder Use</font>',
        ParagraphStyle('', fontSize=7.5, fontName='Helvetica', alignment=TA_CENTER),
    )]]
    ft = Table(ft_data, colWidths=[W])
    ft.setStyle(TableStyle([
        ('LINEABOVE',     (0, 0), (-1, -1), 0.5, LGRAY),
        ('TOPPADDING',    (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(ft)

    doc.build(story)
    buf.seek(0)
    return buf


class PDFRequest(BaseModel):
    user_story: str
    report_data: dict
    review_data: dict
    tc_list: list
    label: Optional[str] = ""
    run_date: Optional[str] = ""


class PDFHistoryRequest(BaseModel):
    run_id: str


@router.post("/api/export/pdf")
def export_pdf(req: PDFRequest):
    buf = _build_pdf(
        user_story=req.user_story,
        report_data=req.report_data,
        review_data=req.review_data,
        tc_list=req.tc_list,
        label=req.label or 'Untitled Run',
        run_date=req.run_date or datetime.now().strftime('%B %d, %Y  %H:%M'),
    )
    safe_label = (req.label or 'report').replace(' ', '_').replace('/', '-')[:40]
    return StreamingResponse(
        buf,
        media_type='application/pdf',
        headers={'Content-Disposition': f'attachment; filename="qa_report_{safe_label}.pdf"'},
    )


@router.post("/api/export/pdf/history")
def export_pdf_history(req: PDFHistoryRequest):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM runs WHERE id=?", (req.run_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Run not found")
    data = dict(row)
    for key in ("tc_list", "report_data", "review_data"):
        try:
            data[key] = json.loads(data[key] or "null") or ([] if key == "tc_list" else {})
        except Exception:
            data[key] = [] if key == "tc_list" else {}
    label = data.get("label") or data.get("preview", "history")[:40]
    run_date = datetime.fromtimestamp(data.get("ts", 0) / 1000).strftime('%B %d, %Y  %H:%M') \
               if data.get("ts") else datetime.now().strftime('%B %d, %Y  %H:%M')
    buf = _build_pdf(
        user_story=data.get("user_story", ""),
        report_data=data.get("report_data", {}),
        review_data=data.get("review_data", {}),
        tc_list=data.get("tc_list", []),
        label=label,
        run_date=run_date,
    )
    safe_label = label.replace(' ', '_').replace('/', '-')[:40]
    return StreamingResponse(
        buf,
        media_type='application/pdf',
        headers={'Content-Disposition': f'attachment; filename="qa_report_{safe_label}.pdf"'},
    )
