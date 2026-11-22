import { apiClient } from "./apiClient";
import type { ReviewSummaryOut } from "@/types/review";

export async function getReviewSummary(productId: string): Promise<ReviewSummaryOut> {
  const { data } = await apiClient.get<ReviewSummaryOut>(`/products/${productId}/reviews`);
  return data;
}
