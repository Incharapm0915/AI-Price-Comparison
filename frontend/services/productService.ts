import { apiClient } from "./apiClient";
import type { ProductOut } from "@/types/product";

export async function getProduct(productId: string): Promise<ProductOut> {
  const { data } = await apiClient.get<ProductOut>(`/products/${productId}`);
  return data;
}
