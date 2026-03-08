export interface FieldPipelineInfo {
  pipeline_id: string;
  pipeline_name: string;
}

export interface FieldFrequencyRow {
  field_name: string;
  frequency: number;
  pipelines: FieldPipelineInfo[];
}

export interface SchemaMatrixResponse {
  fields: FieldFrequencyRow[];
}
