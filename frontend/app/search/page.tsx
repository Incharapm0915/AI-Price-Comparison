import Link from "next/link";

import { ProductCard } from "@/components/ProductCard";
import { SearchBar } from "@/components/SearchBar";
import { search } from "@/services/searchService";

export default async function SearchResultsPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string }>;
}) {
  const { q } = await searchParams;
  const query = (q ?? "").trim();

  if (!query) {
    return (
      <main className="mx-auto max-w-3xl px-6 py-12 text-center">
        <p className="text-gray-600">Type something to search for.</p>
        <Link href="/" className="mt-4 inline-block text-brand-600 hover:underline">
          Back to search
        </Link>
      </main>
    );
  }

  let result;
  let error: string | null = null;
  try {
    result = await search({ query });
  } catch {
    error = "Something went wrong reaching the search service. Please try again.";
  }

  return (
    <main className="mx-auto max-w-3xl px-6 py-8">
      <div className="mb-6">
        <SearchBar initialQuery={query} />
      </div>

      {error && <p className="text-red-600">{error}</p>}

      {result && (
        <>
          <p className="mb-4 text-sm text-gray-500">
            {result.groups.length} result{result.groups.length === 1 ? "" : "s"} for &ldquo;{query}&rdquo;
            {result.retailers_failed.length > 0 && (
              <span className="ml-2 text-amber-600">
                ({result.retailers_failed.join(", ")} unavailable right now)
              </span>
            )}
          </p>

          {result.groups.length === 0 ? (
            <p className="text-gray-600">No matching products found. Try a different search.</p>
          ) : (
            <div className="flex flex-col gap-4">
              {result.groups.map((group) => (
                <ProductCard key={group.product_id} group={group} />
              ))}
            </div>
          )}
        </>
      )}
    </main>
  );
}
