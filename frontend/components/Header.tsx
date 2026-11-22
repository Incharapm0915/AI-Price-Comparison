import Link from "next/link";

export function Header() {
  return (
    <header className="border-b border-gray-200 bg-white">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <Link href="/" className="text-lg font-bold text-brand-700">
          PriceWise
        </Link>
        <nav className="flex gap-5 text-sm font-medium text-gray-600">
          <Link href="/" className="hover:text-brand-600">
            Search
          </Link>
          <Link href="/alerts" className="hover:text-brand-600">
            My alerts
          </Link>
        </nav>
      </div>
    </header>
  );
}
