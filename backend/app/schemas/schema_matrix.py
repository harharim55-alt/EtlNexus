from pydantic import BaseModel


class FieldPipelineInfo(BaseModel):
    pipeline_id: str
    pipeline_name: str


class FieldFrequencyRow(BaseModel):
    field_name: str
    frequency: int
    pipelines: list[FieldPipelineInfo]


class SchemaMatrixResponse(BaseModel):
    fields: list[FieldFrequencyRow]
