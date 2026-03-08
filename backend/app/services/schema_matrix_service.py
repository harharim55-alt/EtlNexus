from app.repositories.field_frequency_repo import FieldFrequencyRepository
from app.schemas.schema_matrix import (
    FieldFrequencyRow,
    FieldPipelineInfo,
    SchemaMatrixResponse,
)


class SchemaMatrixService:
    def __init__(self, field_freq_repo: FieldFrequencyRepository):
        self.field_freq_repo = field_freq_repo

    async def get_schema_matrix(self) -> SchemaMatrixResponse:
        frequencies = await self.field_freq_repo.get_field_frequencies()
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
        return SchemaMatrixResponse(fields=rows)
