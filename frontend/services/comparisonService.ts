import { apiClient } from "./apiClient";
import type { ComparisonOut } from "@/types/comparison";

export async function getComparison(productId: string): Promise<ComparisonOut> {
  const { data } = await apiClient.get<ComparisonOut>(`/products/${productId}/compare`);
  return data;
}
