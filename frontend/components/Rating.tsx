export function Rating({ value, count }: { value: number | null; count?: number | null }) {
  if (value === null) {
    return <span className="text-sm text-gray-400">No ratings yet</span>;
  }
  return (
    <span className="inline-flex items-center gap-1 text-sm">
      <span className="font-medium text-amber-600">★ {value.toFixed(1)}</span>
      {count ? <span className="text-gray-500">({count.toLocaleString("en-IN")})</span> : null}
    </span>
  );
}
