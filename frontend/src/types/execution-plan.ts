export interface ExecutionPlanNode {
  id: number;
  name: string;
  type: "read" | "write" | "shuffle" | "transform";
  detail: string;
  full_detail: string;
  metrics: Record<string, string>;
  children: ExecutionPlanNode[];
}

export interface ExecutionPlanRunSummary {
  dag_run_id: string;
  dag_id: string;
  start_date: string | null;
  status: string;
}

export interface ExecutionPlanRunsResponse {
  items: ExecutionPlanRunSummary[];
  total: number;
}

export interface ExecutionPlanResponse {
  dag_id: string;
  dag_run_id: string;
  task_id: string;
  status: string;
  duration_seconds: number | null;
  execution_date: string | null;
  execution_plan: ExecutionPlanNode | null;
}
