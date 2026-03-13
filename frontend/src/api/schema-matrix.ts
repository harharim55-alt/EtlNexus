import apiClient from "./client";
import type { SchemaMatrixResponse } from "@/types/schema-matrix";

export async function fetchSchemaMatrix(
  skip = 0,
  limit = 200,
): Promise<SchemaMatrixResponse> {
  const { data } = await apiClient.get<SchemaMatrixResponse>("/schema-matrix", {
    params: { skip, limit },
  });
  return data;
}
