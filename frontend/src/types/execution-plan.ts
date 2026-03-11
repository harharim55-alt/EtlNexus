export interface ExecutionPlanNode {
  id: number;
  name: string;
  type: "read" | "write" | "shuffle" | "transform";
  detail: string;
  full_detail: string;
  metrics: Record<string, string>;
  children: ExecutionPlanNode[];
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
