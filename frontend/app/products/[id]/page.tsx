import Image from "next/image";
import Link from "next/link";
import { notFound } from "next/navigation";

import { PriceHistoryChart } from "@/components/PriceHistoryChart";
import { RecommendationsSection } from "@/components/RecommendationsSection";
import { ReviewSummary } from "@/components/ReviewSummary";
import { getPriceHistory } from "@/services/priceService";
import { getProduct } from "@/services/productService";
import { getRecommendations } from "@/services/recommendationService";
import { getReviewSummary } from "@/services/reviewsService";
import { formatPrice } from "@/utils/format";

export default async function ProductDetailsPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;

  let product;
  try {
    product = await getProduct(id);
  } catch {
    notFound();
  }
  if (!product) notFound();

  // Independent sections — one failing (e.g. no reviews collected yet)
  // must not take the whole page down.
  const [priceHistory, reviewSummary, recommendations] = await Promise.all([
    getPriceHistory(id).catch(() => null),
    getReviewSummary(id).catch(() => null),
    getRecommendations(id).catch(() => null),
  ]);

  const bestListing = product.listings
    .filter((l) => l.price !== null)
    .sort((a, b) => (a.price as number) - (b.price as number))[0];

  return (
    <main className="mx-auto max-w-5xl px-6 py-8">
      <div className="grid gap-8 md:grid-cols-2">
        <div className="relative aspect-square overflow-hidden rounded-xl bg-gray-50">
          {product.image_urls[0] ? (
            <Image src={product.image_urls[0]} alt={product.canonical_name} fill unoptimized className="object-contain" />
          ) : (
            <div className="flex h-full items-center justify-center text-gray-400">No image</div>
          )}
        </div>

        <div>
          <h1 className="text-2xl font-bold text-gray-900">{product.canonical_name}</h1>
          {product.brand && <p className="mt-1 text-gray-500">{product.brand}</p>}
          {product.description && <p className="mt-3 text-sm text-gray-600">{product.description}</p>}

          {bestListing && (
            <p className="mt-4 text-2xl font-bold text-gray-900">{formatPrice(bestListing.price)}</p>
          )}

          <Link
            href={`/products/${id}/compare`}
            className="mt-4 inline-block rounded-lg bg-brand-600 px-5 py-2.5 font-medium text-white hover:bg-brand-700"
          >
            Compare across {product.listings.length} retailer{product.listings.length === 1 ? "" : "s"}
          </Link>
        </div>
      </div>

      {Object.keys(product.specifications).length > 0 && (
        <Section title="Specifications">
          <dl className="grid grid-cols-1 gap-x-8 gap-y-2 sm:grid-cols-2">
            {Object.entries(product.specifications).map(([key, value]) => (
              <div key={key} className="flex justify-between border-b border-gray-100 py-1.5 text-sm last:border-0">
                <dt className="text-gray-500">{key}</dt>
                <dd className="font-medium text-gray-900">{value}</dd>
              </div>
            ))}
          </dl>
        </Section>
      )}

      {priceHistory && (
        <Section title="Price history">
          <PriceHistoryChart history={priceHistory} />
        </Section>
      )}

      {reviewSummary && (
        <Section title="Reviews">
          <ReviewSummary summary={reviewSummary} />
        </Section>
      )}

      {recommendations && (
        <Section title="Recommendations">
          <RecommendationsSection recommendations={recommendations} />
        </Section>
      )}
    </main>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mt-8">
      <h2 className="mb-3 text-lg font-semibold text-gray-900">{title}</h2>
      <div className="rounded-xl border border-gray-200 bg-white p-4">{children}</div>
    </section>
  );
}
