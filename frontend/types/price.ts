export interface PriceHistoryPoint {
  retailer: string;
  price: number;
  mrp: number | null;
  discount: number | null;
  availability: string;
  collected_at: string;
}

export interface ProductPriceHistoryOut {
  product_id: string;
  currency: string;
  highest: number | null;
  lowest: number | null;
  current: number | null;
  average: number | null;
  points: PriceHistoryPoint[];
}

export interface PricePredictionOut {
  listing_id: string;
  retailer: string;
  currency: string;
  current_price: number | null;
  predicted_price: number | null;
  predicted_range_low: number | null;
  predicted_range_high: number | null;
  trend: "UP" | "DOWN" | "STABLE" | "INSUFFICIENT_DATA";
  confidence: number | null;
  days_of_history: number;
}
