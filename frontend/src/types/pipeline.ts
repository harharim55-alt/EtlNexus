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
  success_rate: number | null;
  team: string | null;
}

export interface PipelineDetail {
  id: string;
  name: string;
  task_id: string | null;
  description: string | null;
  category: string | null;
  schedule: string | null;
  rows_per_day: string | null;
  airflow_status: string;
  fields: PipelineField[];
  source_tables: string[];
  destination_tables: string[];
  documentation: string | null;
  last_updated_by: string | null;
  last_updated_at: string | null;
  created_at: string | null;
  updated_at: string | null;
  team: string | null;
  team_id: string | null;
  can_edit: boolean;
}

export interface PipelineUpdateRequest {
  description?: string | null;
  documentation?: string | null;
}

export interface PipelineUpdateResponse {
  id: string;
  description: string | null;
  documentation: string | null;
  last_updated_by: string | null;
  last_updated_at: string | null;
}

export interface JoinSuggestion {
  pipeline_id: string;
  pipeline_name: string;
  shared_fields: string[];
}

export interface JoinSuggestionsResponse {
  schema_matches: JoinSuggestion[];
}
