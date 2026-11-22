import type { ListingOut } from "@/types/product";
import { formatPrice, formatRetailer } from "@/utils/format";
import { Badge } from "./Badge";
import { Rating } from "./Rating";
import { SetAlertButton } from "./SetAlertButton";

const RETAILER_STYLES: Record<string, string> = {
  amazon: "border-amber-300",
  flipkart: "border-blue-300",
};

export function RetailerListingCard({
  listing,
  highlights,
}: {
  listing: ListingOut;
  highlights?: { bestPrice?: boolean; bestRating?: boolean; bestDiscount?: boolean; bestValue?: boolean };
}) {
  const borderClass = RETAILER_STYLES[listing.retailer] ?? "border-gray-200";

  return (
    <div className={`flex flex-col gap-2 rounded-xl border-2 bg-white p-4 shadow-sm ${borderClass}`}>
      <div className="flex items-center justify-between">
        <span className="text-sm font-semibold uppercase tracking-wide text-gray-500">
          {formatRetailer(listing.retailer)}
        </span>
        <div className="flex gap-1">
          {highlights?.bestPrice && <Badge variant="success">Best price</Badge>}
          {highlights?.bestRating && <Badge variant="info">Best rated</Badge>}
          {highlights?.bestDiscount && <Badge variant="warning">Best discount</Badge>}
          {highlights?.bestValue && <Badge variant="success">Best value</Badge>}
        </div>
      </div>

      <div className="flex items-baseline gap-2">
        <span className="text-2xl font-bold text-gray-900">{formatPrice(listing.price, listing.currency)}</span>
        {listing.mrp && listing.mrp > (listing.price ?? 0) && (
          <span className="text-sm text-gray-400 line-through">{formatPrice(listing.mrp, listing.currency)}</span>
        )}
        {listing.discount_percent ? (
          <span className="text-sm font-medium text-emerald-600">{listing.discount_percent}% off</span>
        ) : null}
      </div>

      <Rating value={listing.rating} count={listing.rating_count} />

      {listing.review_count ? (
        <span className="text-xs text-gray-500">{listing.review_count.toLocaleString("en-IN")} reviews</span>
      ) : null}

      <span
        className={`text-xs font-medium ${
          listing.availability === "IN_STOCK" ? "text-emerald-600" : "text-red-500"
        }`}
      >
        {listing.availability.replace("_", " ")}
      </span>

      {listing.seller_name && <span className="text-xs text-gray-500">Sold by {listing.seller_name}</span>}

      {listing.offers.length > 0 && (
        <ul className="mt-1 space-y-0.5 text-xs text-gray-600">
          {listing.offers.map((offer, i) => (
            <li key={i}>• {offer}</li>
          ))}
        </ul>
      )}

      <a
        href={listing.product_url}
        target="_blank"
        rel="noopener noreferrer"
        className="mt-2 rounded-lg bg-gray-900 px-4 py-2 text-center text-sm font-medium text-white hover:bg-gray-800"
      >
        View on {formatRetailer(listing.retailer)}
      </a>

      <SetAlertButton listingId={listing.id} currentPrice={listing.price} />
    </div>
  );
}
