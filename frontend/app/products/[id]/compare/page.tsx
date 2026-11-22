import Link from "next/link";
import { notFound } from "next/navigation";

import { RetailerListingCard } from "@/components/RetailerListingCard";
import { getComparison } from "@/services/comparisonService";
import { formatPrice, formatRetailer } from "@/utils/format";

export default async function ComparePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;

  let comparison;
  try {
    comparison = await getComparison(id);
  } catch {
    notFound();
  }
  if (!comparison) notFound();

  return (
    <main className="mx-auto max-w-5xl px-6 py-8">
      <Link href={`/products/${id}`} className="text-sm text-brand-600 hover:underline">
        ← Full product details
      </Link>

      <h1 className="mt-2 text-2xl font-bold text-gray-900">{comparison.canonical_name}</h1>
      {comparison.brand && <p className="text-gray-500">{comparison.brand}</p>}

      {comparison.best_price !== null && (
        <div className="mt-4 rounded-xl bg-brand-50 p-4 text-brand-900">
          <p className="text-sm">
            Best price: <span className="font-semibold">{formatPrice(comparison.best_price)}</span> on{" "}
            <span className="font-semibold">
              {comparison.best_price_retailer && formatRetailer(comparison.best_price_retailer)}
            </span>
            {comparison.savings_vs_highest ? (
              <span> — you save {formatPrice(comparison.savings_vs_highest)} vs. the highest listed price.</span>
            ) : null}
          </p>
        </div>
      )}

      <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {comparison.listings.map((listing) => (
          <RetailerListingCard
            key={listing.id}
            listing={listing}
            highlights={{
              bestPrice: listing.retailer === comparison.best_price_retailer,
              bestRating: listing.retailer === comparison.best_rated_retailer,
              bestDiscount: listing.retailer === comparison.best_discount_retailer,
              bestValue: listing.retailer === comparison.best_value_retailer,
            }}
          />
        ))}
      </div>

      {Object.keys(comparison.specifications).length > 0 && (
        <section className="mt-8">
          <h2 className="mb-3 text-lg font-semibold text-gray-900">Specifications</h2>
          <dl className="grid grid-cols-1 gap-x-8 gap-y-2 rounded-xl border border-gray-200 bg-white p-4 sm:grid-cols-2">
            {Object.entries(comparison.specifications).map(([key, value]) => (
              <div key={key} className="flex justify-between border-b border-gray-100 py-1.5 text-sm last:border-0">
                <dt className="text-gray-500">{key}</dt>
                <dd className="font-medium text-gray-900">{value}</dd>
              </div>
            ))}
          </dl>
        </section>
      )}
    </main>
  );
}
