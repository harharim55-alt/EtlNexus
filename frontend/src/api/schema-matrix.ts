import apiClient from "./client";
import type { SchemaMatrixResponse } from "@/types/schema-matrix";

export async function fetchSchemaMatrix(
  skip = 0,
  limit = 200,
  q?: string,
): Promise<SchemaMatrixResponse> {
  const { data } = await apiClient.get<SchemaMatrixResponse>("/schema-matrix", {
    params: { skip, limit, ...(q ? { q } : {}) },
  });
  return data;
}
