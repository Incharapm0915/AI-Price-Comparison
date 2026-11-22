export interface SimilarProductOut {
  product_id: string;
  canonical_name: string;
  brand: string | null;
  image_url: string | null;
  best_price: number | null;
  average_rating: number | null;
}

export interface RecommendationsOut {
  product_id: string;
  recommended_for: string[];
  not_ideal_for: string[];
  similar_products: SimilarProductOut[];
}
