export interface ListingOut {
  id: string;
  retailer: string;
  retailer_product_id: string;
  product_name: string;
  product_url: string;
  price: number | null;
  mrp: number | null;
  discount_percent: number | null;
  currency: string;
  offers: string[];
  rating: number | null;
  rating_count: number | null;
  review_count: number | null;
  rating_breakdown: Record<string, number> | null;
  availability: string;
  seller_name: string | null;
  seller_rating: number | null;
  image_urls: string[];
  specifications: Record<string, string>;
  match_status: string | null;
  match_score: number | null;
  collected_at: string;
}

export interface ProductOut {
  id: string;
  common_product_id: string;
  brand: string | null;
  model: string | null;
  variant: string | null;
  category: string | null;
  subcategory: string | null;
  canonical_name: string;
  description: string | null;
  specifications: Record<string, string>;
  image_urls: string[];
  listings: ListingOut[];
  created_at: string;
  updated_at: string;
}

export interface SearchResultGroup {
  product_id: string;
  canonical_name: string;
  brand: string | null;
  image_url: string | null;
  best_price: number | null;
  best_price_retailer: string | null;
  retailer_count: number;
  average_rating: number | null;
  total_review_count: number | null;
  listings: ListingOut[];
}
