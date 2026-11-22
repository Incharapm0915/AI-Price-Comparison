"use client";

import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { ProductPriceHistoryOut } from "@/types/price";
import { formatDate, formatPrice } from "@/utils/format";

const RETAILER_COLORS: Record<string, string> = {
  amazon: "#d97706",
  flipkart: "#2563eb",
};

export function PriceHistoryChart({ history }: { history: ProductPriceHistoryOut }) {
  if (history.points.length === 0) {
    return <p className="text-sm text-gray-500">No price history yet — check back after the next collection.</p>;
  }

  const retailers = Array.from(new Set(history.points.map((p) => p.retailer)));

  // Recharts wants one row per x-value with a column per series; pivot the
  // long-format points (retailer, price, collected_at) into that shape.
  const byDate = new Map<string, Record<string, number | string>>();
  for (const point of history.points) {
    const key = point.collected_at;
    const row = byDate.get(key) ?? { collected_at: key };
    row[point.retailer] = point.price;
    byDate.set(key, row);
  }
  const data = Array.from(byDate.values()).sort(
    (a, b) => new Date(a.collected_at as string).getTime() - new Date(b.collected_at as string).getTime()
  );

  return (
    <div>
      <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Stat label="Highest" value={formatPrice(history.highest, history.currency)} />
        <Stat label="Lowest" value={formatPrice(history.lowest, history.currency)} />
        <Stat label="Current" value={formatPrice(history.current, history.currency)} emphasize />
        <Stat label="Average" value={formatPrice(history.average, history.currency)} />
      </div>

      <div className="h-72 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis
              dataKey="collected_at"
              tickFormatter={(v) => formatDate(v as string)}
              tick={{ fontSize: 12 }}
            />
            <YAxis tickFormatter={(v) => formatPrice(v as number, history.currency)} tick={{ fontSize: 12 }} width={90} />
            <Tooltip
              labelFormatter={(v) => formatDate(v as string)}
              formatter={(value: number) => formatPrice(value, history.currency)}
            />
            <Legend />
            {retailers.map((retailer) => (
              <Line
                key={retailer}
                type="monotone"
                dataKey={retailer}
                name={retailer}
                stroke={RETAILER_COLORS[retailer] ?? "#6b7280"}
                connectNulls
                dot={{ r: 3 }}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function Stat({ label, value, emphasize }: { label: string; value: string; emphasize?: boolean }) {
  return (
    <div className="rounded-lg border border-gray-200 bg-gray-50 p-3">
      <div className="text-xs uppercase tracking-wide text-gray-500">{label}</div>
      <div className={emphasize ? "text-lg font-bold text-brand-700" : "text-lg font-semibold text-gray-900"}>
        {value}
      </div>
    </div>
  );
}
