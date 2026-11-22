import Link from "next/link";
import Image from "next/image";

import type { SearchResultGroup } from "@/types/product";
import { formatPrice, formatRetailer } from "@/utils/format";
import { Badge } from "./Badge";
import { Rating } from "./Rating";

export function ProductCard({ group }: { group: SearchResultGroup }) {
  return (
    <div className="flex gap-4 rounded-xl border border-gray-200 bg-white p-4 shadow-sm transition hover:shadow-md">
      <div className="relative h-24 w-24 shrink-0 overflow-hidden rounded-lg bg-gray-50">
        {group.image_url ? (
          // Demo-only image URLs (https://example.com/demo/...) — unoptimized
          // avoids Next.js Image trying to fetch/optimize a non-real host.
          <Image
            src={group.image_url}
            alt={group.canonical_name}
            fill
            unoptimized
            className="object-contain"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center text-xs text-gray-400">No image</div>
        )}
      </div>

      <div className="flex flex-1 flex-col gap-1.5">
        <h3 className="font-medium text-gray-900">{group.canonical_name}</h3>
        <Rating value={group.average_rating} count={group.total_review_count} />

        <div className="mt-1 flex flex-wrap items-center gap-2">
          <span className="text-lg font-semibold text-gray-900">{formatPrice(group.best_price)}</span>
          {group.best_price_retailer && (
            <Badge variant="success">Best on {formatRetailer(group.best_price_retailer)}</Badge>
          )}
          <Badge variant="info">
            {group.retailer_count} retailer{group.retailer_count === 1 ? "" : "s"}
          </Badge>
        </div>

        <div className="mt-2 flex gap-2">
          <Link
            href={`/products/${group.product_id}/compare`}
            className="rounded-lg bg-brand-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-brand-700"
          >
            Compare prices
          </Link>
          <Link
            href={`/products/${group.product_id}`}
            className="rounded-lg border border-gray-300 px-4 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            View details
          </Link>
        </div>
      </div>
    </div>
  );
}
