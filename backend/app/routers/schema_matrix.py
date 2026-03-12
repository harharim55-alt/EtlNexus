from fastapi import APIRouter, Depends

from app.auth import get_current_user
from app.dependencies import get_schema_matrix_service
from app.models.user import User
from app.schemas.schema_matrix import SchemaMatrixResponse
from app.services.schema_matrix_service import SchemaMatrixService

router = APIRouter(prefix="/api/schema-matrix", tags=["schema-matrix"])


@router.get("", response_model=SchemaMatrixResponse)
async def get_schema_matrix(
    user: User = Depends(get_current_user),
    service: SchemaMatrixService = Depends(get_schema_matrix_service),
):
    return await service.get_schema_matrix()
