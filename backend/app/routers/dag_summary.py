"""DAG summary/statistics endpoint."""

from fastapi import APIRouter, Depends

from app.dependencies import get_dag_summary_service
from app.schemas.dag_summary import DagSummaryResponse
from app.services.dag_summary_service import DagSummaryService

router = APIRouter(prefix="/api/dags", tags=["dag-summary"])


@router.get("/summary", response_model=DagSummaryResponse)
async def get_dag_summary(
    service: DagSummaryService = Depends(get_dag_summary_service),
):
    return await service.get_dag_summaries()
