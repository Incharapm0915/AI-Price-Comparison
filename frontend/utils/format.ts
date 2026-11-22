export function formatPrice(price: number | null | undefined, currency = "INR"): string {
  if (price === null || price === undefined) return "—";
  const symbol = currency === "INR" ? "₹" : currency + " ";
  return `${symbol}${price.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
}

export function formatRetailer(retailer: string): string {
  return retailer.charAt(0).toUpperCase() + retailer.slice(1);
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString("en-IN", { year: "numeric", month: "short", day: "numeric" });
}

export function formatPercent(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return `${value}%`;
}
