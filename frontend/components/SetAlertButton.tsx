"use client";

import { useState } from "react";

import { createAlert } from "@/services/alertService";
import { formatPrice } from "@/utils/format";

export function SetAlertButton({ listingId, currentPrice }: { listingId: string; currentPrice: number | null }) {
  const [open, setOpen] = useState(false);
  const [email, setEmail] = useState("");
  const [targetPrice, setTargetPrice] = useState(currentPrice ? String(Math.round(currentPrice * 0.9)) : "");
  const [status, setStatus] = useState<"idle" | "saving" | "done" | "error">("idle");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setStatus("saving");
    try {
      await createAlert({ listing_id: listingId, email, target_price: Number(targetPrice) });
      setStatus("done");
    } catch {
      setStatus("error");
    }
  }

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="mt-1 text-xs font-medium text-brand-600 underline-offset-2 hover:underline"
      >
        Notify me on a price drop
      </button>
    );
  }

  if (status === "done") {
    return <p className="mt-1 text-xs text-emerald-600">You&apos;ll get an email when it drops to {formatPrice(Number(targetPrice))}.</p>;
  }

  return (
    <form onSubmit={handleSubmit} className="mt-2 space-y-1.5 rounded-lg border border-gray-200 bg-gray-50 p-2">
      <input
        type="email"
        required
        placeholder="you@example.com"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        className="w-full rounded border border-gray-300 px-2 py-1 text-xs"
      />
      <input
        type="number"
        required
        min={1}
        placeholder="Target price"
        value={targetPrice}
        onChange={(e) => setTargetPrice(e.target.value)}
        className="w-full rounded border border-gray-300 px-2 py-1 text-xs"
      />
      <div className="flex gap-1.5">
        <button
          type="submit"
          disabled={status === "saving"}
          className="rounded bg-brand-600 px-2 py-1 text-xs font-medium text-white hover:bg-brand-700 disabled:opacity-50"
        >
          {status === "saving" ? "Saving…" : "Set alert"}
        </button>
        <button type="button" onClick={() => setOpen(false)} className="text-xs text-gray-500 hover:underline">
          Cancel
        </button>
      </div>
      {status === "error" && <p className="text-xs text-red-500">Couldn&apos;t save that alert. Try again.</p>}
    </form>
  );
}
