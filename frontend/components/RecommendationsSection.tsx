import Link from "next/link";

import type { RecommendationsOut } from "@/types/recommendation";
import { formatPrice } from "@/utils/format";
import { Badge } from "./Badge";
import { Rating } from "./Rating";

export function RecommendationsSection({ recommendations }: { recommendations: RecommendationsOut }) {
  const { recommended_for, not_ideal_for, similar_products } = recommendations;
  const hasUseCases = recommended_for.length > 0 || not_ideal_for.length > 0;

  return (
    <div className="space-y-6">
      {hasUseCases && (
        <div className="grid gap-4 sm:grid-cols-2">
          {recommended_for.length > 0 && (
            <div>
              <h4 className="mb-2 text-sm font-semibold text-gray-700">Recommended for</h4>
              <div className="flex flex-wrap gap-1.5">
                {recommended_for.map((label) => (
                  <Badge key={label} variant="success">
                    {label}
                  </Badge>
                ))}
              </div>
            </div>
          )}
          {not_ideal_for.length > 0 && (
            <div>
              <h4 className="mb-2 text-sm font-semibold text-gray-700">Not ideal for</h4>
              <div className="flex flex-wrap gap-1.5">
                {not_ideal_for.map((label) => (
                  <Badge key={label} variant="warning">
                    {label}
                  </Badge>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {similar_products.length > 0 && (
        <div>
          <h4 className="mb-2 text-sm font-semibold text-gray-700">Similar products</h4>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {similar_products.map((p) => (
              <Link
                key={p.product_id}
                href={`/products/${p.product_id}`}
                className="rounded-lg border border-gray-200 p-3 transition hover:border-brand-300 hover:shadow-sm"
              >
                <p className="line-clamp-2 text-sm font-medium text-gray-900">{p.canonical_name}</p>
                <div className="mt-1 flex items-center justify-between">
                  <span className="text-sm font-semibold text-gray-900">{formatPrice(p.best_price)}</span>
                  <Rating value={p.average_rating} />
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
