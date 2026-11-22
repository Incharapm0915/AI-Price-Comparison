export interface CreateAlertRequest {
  listing_id: string;
  email: string;
  target_price: number;
}

export interface AlertOut {
  id: string;
  listing_id: string;
  retailer: string;
  product_name: string;
  email: string;
  target_price: number;
  current_price: number | null;
  status: string;
  triggered_at: string | null;
  triggered_price: number | null;
  created_at: string;
}
