"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

export function SearchBar({ initialQuery = "" }: { initialQuery?: string }) {
  const [query, setQuery] = useState(initialQuery);
  const [isPending, startTransition] = useTransition();
  const router = useRouter();

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = query.trim();
    if (!trimmed) return;
    // startTransition keeps isPending true until the navigated-to page's
    // server-side data fetch resolves — the button reflects that
    // immediately, and app/search/loading.tsx covers the rest of the wait
    // (live-mode search can take 30-90s; without either of these, clicking
    // Search looks like it did nothing).
    startTransition(() => {
      router.push(`/search?q=${encodeURIComponent(trimmed)}`);
    });
  }

  return (
    <form onSubmit={handleSubmit} className="flex w-full max-w-2xl gap-2">
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search for a product, e.g. iPhone 15 128GB Black"
        className="flex-1 rounded-lg border border-gray-300 px-4 py-3 text-base shadow-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/30"
      />
      <button
        type="submit"
        disabled={isPending}
        className="rounded-lg bg-brand-600 px-6 py-3 font-medium text-white transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {isPending ? "Searching…" : "Search"}
      </button>
    </form>
  );
}
