import type { SearchResultGroup } from "./product";

export interface SearchRequest {
  query: string;
  retailers?: string[] | null;
  max_results_per_retailer?: number | null;
}

export interface SearchResponse {
  query: string;
  groups: SearchResultGroup[];
  retailers_searched: string[];
  retailers_failed: string[];
}
