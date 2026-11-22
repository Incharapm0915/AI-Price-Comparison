import { apiClient } from "./apiClient";
import type { RecommendationsOut } from "@/types/recommendation";

export async function getRecommendations(productId: string): Promise<RecommendationsOut> {
  const { data } = await apiClient.get<RecommendationsOut>(`/products/${productId}/recommendations`);
  return data;
}
