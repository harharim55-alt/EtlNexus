import type { PipelineField } from "./pipeline";

export interface TableColumn {
  name: string;
  data_type: string | null;
  ordinal_position: number;
}

export interface TableSchema {
  namespace: string;
  table_name: string;
  columns: TableColumn[];
  consume_snippet: string;
}

export interface TableListResponse {
  items: TableSchema[];
  total: number;
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
