import type { ListingOut } from "./product";

export interface ComparisonOut {
  product_id: string;
  canonical_name: string;
  brand: string | null;
  specifications: Record<string, string>;
  image_urls: string[];
  listings: ListingOut[];

  best_price_retailer: string | null;
  best_price: number | null;
  savings_vs_highest: number | null;

  best_rated_retailer: string | null;
  best_rating: number | null;

  best_discount_retailer: string | null;
  best_discount_percent: number | null;

  best_value_retailer: string | null;
}
