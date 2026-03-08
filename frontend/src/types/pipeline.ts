export interface PipelineField {
  id: string;
  name: string;
  data_type: string | null;
  ordinal_position: number;
}

export interface PipelineListItem {
  id: string;
  name: string;
  description: string | null;
  category: string | null;
  schedule: string | null;
  rows_per_day: string | null;
  airflow_status: string;
}

export interface PipelineDetail {
  id: string;
  name: string;
  description: string | null;
  category: string | null;
  schedule: string | null;
  rows_per_day: string | null;
  airflow_status: string;
  fields: PipelineField[];
  source_tables: string[];
  destination_tables: string[];
  created_at: string | null;
  updated_at: string | null;
}

export interface JoinSuggestion {
  pipeline_id: string;
  pipeline_name: string;
  shared_fields: string[];
}

export interface JoinSuggestionsResponse {
  schema_matches: JoinSuggestion[];
}
