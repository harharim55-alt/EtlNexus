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
        self, skip: int = 0, limit: int = 200
    ) -> SchemaMatrixResponse:
        cache_key = f"matrix:{skip}:{limit}"
        cached = schema_matrix_cache.get(cache_key)
        if cached is not None:
            return cached

        frequencies, total = await self.field_freq_repo.get_field_frequencies(
            skip=skip, limit=limit
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
