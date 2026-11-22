"use client";

import { useState } from "react";

import { deleteAlert, listAlerts } from "@/services/alertService";
import type { AlertOut } from "@/types/alert";
import { formatDate, formatPrice, formatRetailer } from "@/utils/format";

const STATUS_STYLES: Record<string, string> = {
  ACTIVE: "text-brand-600",
  TRIGGERED: "text-emerald-600",
  PAUSED: "text-gray-400",
};

export default function AlertsPage() {
  const [email, setEmail] = useState("");
  const [alerts, setAlerts] = useState<AlertOut[] | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleLookup(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      setAlerts(await listAlerts(email));
    } finally {
      setLoading(false);
    }
  }

  async function handleDelete(id: string) {
    await deleteAlert(id);
    setAlerts((prev) => prev?.filter((a) => a.id !== id) ?? null);
  }

  return (
    <main className="mx-auto max-w-2xl px-6 py-8">
      <h1 className="text-2xl font-bold text-gray-900">My price alerts</h1>
      <p className="mt-1 text-sm text-gray-500">
        Set an alert from any product&apos;s comparison page — look it up here by email.
      </p>

      <form onSubmit={handleLookup} className="mt-4 flex gap-2">
        <input
          type="email"
          required
          placeholder="you@example.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm"
        />
        <button
          type="submit"
          disabled={loading}
          className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
        >
          {loading ? "Loading…" : "Find my alerts"}
        </button>
      </form>

      {alerts !== null && (
        <div className="mt-6 space-y-3">
          {alerts.length === 0 ? (
            <p className="text-sm text-gray-500">No alerts found for that email.</p>
          ) : (
            alerts.map((alert) => (
              <div
                key={alert.id}
                className="flex items-center justify-between rounded-lg border border-gray-200 p-3"
              >
                <div>
                  <p className="text-sm font-medium text-gray-900">{alert.product_name}</p>
                  <p className="text-xs text-gray-500">
                    {formatRetailer(alert.retailer)} · target {formatPrice(alert.target_price)} · current{" "}
                    {formatPrice(alert.current_price)}
                  </p>
                  <p className={`text-xs font-medium ${STATUS_STYLES[alert.status] ?? "text-gray-500"}`}>
                    {alert.status}
                    {alert.triggered_at ? ` on ${formatDate(alert.triggered_at)}` : ""}
                  </p>
                </div>
                <button
                  onClick={() => handleDelete(alert.id)}
                  className="text-xs font-medium text-red-500 hover:underline"
                >
                  Remove
                </button>
              </div>
            ))
          )}
        </div>
      )}
    </main>
  );
}
