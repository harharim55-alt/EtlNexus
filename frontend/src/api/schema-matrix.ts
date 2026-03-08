import apiClient from "./client";
import type { SchemaMatrixResponse } from "@/types/schema-matrix";

export async function fetchSchemaMatrix(): Promise<SchemaMatrixResponse> {
  const { data } = await apiClient.get<SchemaMatrixResponse>("/schema-matrix");
  return data;
}
