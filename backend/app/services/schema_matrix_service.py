import uuid

from app.cache import schema_matrix_cache
from app.repositories.field_frequency_repo import FieldFrequencyRepository
from app.schemas.schema_matrix import (
    FieldFrequencyRow,
    FieldPipelineInfo,
    SchemaMatrixResponse,
)


class SchemaMatrixService:
    def __init__(self, field_freq_repo: FieldFrequencyRepository):
        self.field_freq_repo = field_freq_repo

    async def get_schema_matrix(
        self,
        skip: int = 0,
        limit: int = 200,
        q: str | None = None,
        visible_pipeline_ids: set[uuid.UUID] | None = None,
    ) -> SchemaMatrixResponse:
        """Return schema matrix data, optionally scoped to visible pipelines.

        Args:
            skip: Pagination offset.
            limit: Maximum field rows to return.
            q: Optional field name substring filter.
            visible_pipeline_ids: When provided, restricts fields to those
                belonging to these pipelines (non-admin visibility scoping).
                ``None`` means no restriction (admin or all-pipelines path).
        """
        # Cache key incorporates visibility scope so different users get
        # correctly scoped cached responses.
        scope = "all" if visible_pipeline_ids is None else str(sorted(str(i) for i in visible_pipeline_ids))
        cache_key = f"matrix:{skip}:{limit}:{q or ''}:{scope}"
        cached = schema_matrix_cache.get(cache_key)
        if cached is not None:
            return cached

        frequencies, total = await self.field_freq_repo.get_field_frequencies(
            skip=skip, limit=limit, q=q, visible_pipeline_ids=visible_pipeline_ids
        )
        rows = [
            FieldFrequencyRow(
                field_name=f["field_name"],
                frequency=f["frequency"],
                pipelines=[
                    FieldPipelineInfo(**p) for p in f["pipelines"]
                ],
            )
            for f in frequencies
        ]
        result = SchemaMatrixResponse(fields=rows, total=total)
        schema_matrix_cache.set(cache_key, result)
        return result
