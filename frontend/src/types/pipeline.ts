export interface Tag {
  id: string;
  name: string;
  created_by_team_id: string | null;
  created_at: string | null;
}

export interface PipelineField {
  id: string;
  name: string;
  data_type: string | null;
  ordinal_position: number;
}

export interface PipelineLogNetwork {
  id: string | null;
  network_id: string;
  network_name: string | null;
  retention: string | null;
}

export interface PipelineLog {
  id: string;
  pipeline_id: string;
  name: string;
  ordinal_position: number;
  created_at: string | null;
  networks: PipelineLogNetwork[];
  fields: PipelineField[];
}

export interface PipelineListItem {
  id: string;
  name: string;
  description: string | null;
  category: string | null;
  pipeline_type: string;
  schedule: string | null;
  schedule_type: string | null;
  rows_per_day: string | null;
  airflow_status: string;
  success_rate: number | null;
  team: string | null;
  last_run_at: string | null;
  execution_date: string | null;
  tags: Tag[];
  is_data_product: boolean;
  network_names: string[];
}

export interface PipelineListResponse {
  items: PipelineListItem[];
  total: number;
}

export interface PipelineDetail {
  id: string;
  name: string;
  task_id: string | null;
  description: string | null;
  category: string | null;
  pipeline_type: string;
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
  execution_date: string | null;
  last_checked_at: string | null;
  tags: Tag[];
  how_to_read: string | null;
  import_snippet: string | null;
  schedule_type: string | null;
  schema_manually_edited: boolean;
  topology_enabled: boolean;
  is_data_product: boolean;
  writes_to_manual: string[] | null;
  reads_from_manual: string[] | null;
  feeds_into_manual: string[] | null;
}

export interface PipelineUpdateRequest {
  description?: string | null;
  documentation?: string | null;
  how_to_read?: string | null;
  import_snippet?: string | null;
  schedule_type?: string | null;
  topology_enabled?: boolean;
  writes_to_manual?: string[] | null;
  reads_from_manual?: string[] | null;
  feeds_into_manual?: string[] | null;
}

export interface PipelineUpdateResponse {
  id: string;
  description: string | null;
  documentation: string | null;
  last_updated_by: string | null;
  last_updated_at: string | null;
}

export interface PipelineRevision {
  id: string;
  pipeline_id: string;
  field_name: "description" | "documentation";
  content: string | null;
  changed_by: string;
  change_source: "user" | "restore" | "system";
  created_at: string;
}

export interface RevisionListResponse {
  items: PipelineRevision[];
  total: number;
}

export interface JoinSuggestion {
  pipeline_id: string;
  pipeline_name: string;
  shared_fields: string[];
}

export interface JoinSuggestionsResponse {
  schema_matches: JoinSuggestion[];
}

export interface Network {
  id: string;
  name: string;
  description: string | null;
}

export interface FeatureFlag {
  id: string;
  name: string;
  enabled: boolean;
  beta_only: boolean;
  description: string | null;
}
