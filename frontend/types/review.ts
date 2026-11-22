export interface ReviewOut {
  id: string;
  retailer: string;
  reviewer_name: string | null;
  rating: number | null;
  review_title: string | null;
  review_text: string | null;
  review_date: string | null;
  verified_purchase: boolean | null;
  helpful_count: number | null;
  sentiment: string | null;
  sentiment_score: number | null;
}

export interface ReviewSummaryOut {
  product_id: string;
  total_reviews_analyzed: number;
  positive_percent: number | null;
  neutral_percent: number | null;
  negative_percent: number | null;
  pros: string[];
  cons: string[];
  most_mentioned_features: string[];
  common_complaints: string[];
  retailer_ratings: Record<string, number>;
  sample_reviews: ReviewOut[];
}
