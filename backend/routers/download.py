from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from backend.agents.export import build_excel, build_csv

router = APIRouter()


class DownloadRequest(BaseModel):
    test_cases: list


@router.post("/api/download/excel")
async def download_excel(req: DownloadRequest):
    buf, count = build_excel(req.test_cases)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=qa_test_suite_{count}_cases.xlsx"},
    )


@router.post("/api/download/csv")
async def download_csv(req: DownloadRequest):
    buf, count = build_csv(req.test_cases)
    return StreamingResponse(
        buf,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=qa_test_suite_{count}_cases.csv"},
    )
