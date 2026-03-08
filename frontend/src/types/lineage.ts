export interface LineageNode {
  table_name: string;
  pipeline_id: string | null;
  pipeline_name: string | null;
  node_type: "source" | "target" | "pipeline";
}

export interface LineageEdge {
  source: string;
  target: string;
  edge_type: string;
}

export interface LineageGraph {
  nodes: LineageNode[];
  edges: LineageEdge[];
  source_tables: string[];
  destination_tables: string[];
}
