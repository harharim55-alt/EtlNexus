import uuid

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_dag_network_repo, get_pipeline_repo
from app.repositories.dag_network_repo import DagNetworkRepository
from app.repositories.pipeline_repo import PipelineRepository
from app.schemas.dag_network import DagNetworkSchema, DagNetworksResponse

router = APIRouter(prefix="/api/pipelines", tags=["dag-networks"])


@router.get("/{pipeline_id}/dags", response_model=DagNetworksResponse)
async def get_dag_networks(
    pipeline_id: uuid.UUID,
    pipeline_repo: PipelineRepository = Depends(get_pipeline_repo),
    dag_repo: DagNetworkRepository = Depends(get_dag_network_repo),
):
    pipeline = await pipeline_repo.get_by_id(pipeline_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    networks = await dag_repo.get_by_pipeline_id(pipeline_id)
    return DagNetworksResponse(
        pipeline_id=str(pipeline_id),
        networks=[DagNetworkSchema.model_validate(n) for n in networks],
    )
