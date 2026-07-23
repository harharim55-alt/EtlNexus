import type { PipelineField } from "./pipeline";

export interface TableColumn {
  name: string;
  data_type: string | null;
  ordinal_position: number;
}

/** A reference to a catalog table (no schema). */
export interface TableRef {
  namespace: string;
  table_name: string;
}

export interface TableListItem {
  namespace: string;
  table_name: string;
}

export interface TableListResponse {
  items: TableListItem[];
  total: number;
}

export interface NamespaceListResponse {
  items: string[];
}

/** A table's live schema (columns) + consume snippet, fetched on demand. */
export interface TableSchema {
  namespace: string;
  table_name: string;
  columns: TableColumn[];
  consume_snippet: string;
}

/** Adapt catalog columns to the PipelineField shape SchemaViewer expects. */
export function columnsToFields(table: TableSchema): PipelineField[] {
  return table.columns.map((c) => ({
    id: `${table.namespace}.${table.table_name}.${c.name}`,
    name: c.name,
    data_type: c.data_type,
    ordinal_position: c.ordinal_position,
  }));
}
