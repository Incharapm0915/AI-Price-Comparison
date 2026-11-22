import { SearchBar } from "@/components/SearchBar";

export default function HomePage() {
  return (
    <main className="mx-auto flex min-h-[calc(100vh-65px)] max-w-3xl flex-col items-center justify-center gap-6 px-6 text-center">
      <h1 className="text-4xl font-bold text-gray-900">
        Compare prices across <span className="text-brand-600">Amazon</span> &amp;{" "}
        <span className="text-brand-600">Flipkart</span>
      </h1>
      <p className="max-w-xl text-gray-600">
        Search once — we find the same product on every retailer, even when they word the
        listing differently, and show you the best price, rating, and deal in one place.
      </p>
      <SearchBar />
    </main>
  );
}
