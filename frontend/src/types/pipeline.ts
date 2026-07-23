import type { TableRef } from "./table";

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
  schedule_type: string | null;
  team: string | null;
}

export interface PipelineListResponse {
  items: PipelineListItem[];
  total: number;
}

export interface PipelineDetail {
  id: string;
  name: string;
  description: string | null;
  // The catalog tables that make up this data product (schema fetched per table on demand).
  tables: TableRef[];
  documentation: string | null;
  last_updated_by: string | null;
  last_updated_at: string | null;
  created_at: string | null;
  updated_at: string | null;
  team: string | null;
  can_edit: boolean;
  // Env-templated product-level (read_by_tag) consume snippet.
  default_import_snippet: string;
  schedule_type: string | null;
}

export interface PipelineUpdateRequest {
  name?: string | null;
  description?: string | null;
  documentation?: string | null;
  schedule_type?: string | null;
}

export interface PipelineUpdateResponse {
  id: string;
  name: string;
  description: string | null;
  documentation: string | null;
  schedule_type: string | null;
  last_updated_by: string | null;
  last_updated_at: string | null;
}

export interface PipelineRevision {
  id: string;
  product_id: string;
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
