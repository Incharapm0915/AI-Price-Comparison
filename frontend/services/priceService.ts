import { apiClient } from "./apiClient";
import type { PricePredictionOut, ProductPriceHistoryOut } from "@/types/price";

export async function getPriceHistory(productId: string): Promise<ProductPriceHistoryOut> {
  const { data } = await apiClient.get<ProductPriceHistoryOut>(`/products/${productId}/price-history`);
  return data;
}

export async function getPricePrediction(productId: string): Promise<PricePredictionOut[]> {
  const { data } = await apiClient.get<PricePredictionOut[]>(`/products/${productId}/price-prediction`);
  return data;
}
