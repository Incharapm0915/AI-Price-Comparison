import { apiClient } from "./apiClient";
import type { SearchRequest, SearchResponse } from "@/types/search";

export async function search(payload: SearchRequest): Promise<SearchResponse> {
  const { data } = await apiClient.post<SearchResponse>("/search", payload);
  return data;
}
