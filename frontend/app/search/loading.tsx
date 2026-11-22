export default function SearchLoading() {
  return (
    <main className="mx-auto max-w-3xl px-6 py-8">
      <div className="mb-6 h-[52px] w-full max-w-2xl animate-pulse rounded-lg bg-gray-200" />

      <div className="mb-4 flex items-center gap-2 text-sm text-gray-500">
        <span className="h-4 w-4 animate-spin rounded-full border-2 border-gray-300 border-t-brand-600" />
        Searching Amazon &amp; Flipkart — this can take up to a minute in live mode…
      </div>

      <div className="flex flex-col gap-4">
        {[0, 1, 2].map((i) => (
          <div key={i} className="flex gap-4 rounded-xl border border-gray-200 bg-white p-4">
            <div className="h-24 w-24 shrink-0 animate-pulse rounded-lg bg-gray-100" />
            <div className="flex flex-1 flex-col gap-2">
              <div className="h-4 w-3/4 animate-pulse rounded bg-gray-100" />
              <div className="h-3 w-1/3 animate-pulse rounded bg-gray-100" />
              <div className="mt-1 h-6 w-1/4 animate-pulse rounded bg-gray-100" />
            </div>
          </div>
        ))}
      </div>
    </main>
  );
}
