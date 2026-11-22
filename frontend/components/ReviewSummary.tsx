import type { ReviewSummaryOut } from "@/types/review";
import { formatDate, formatRetailer } from "@/utils/format";
import { Badge } from "./Badge";

export function ReviewSummary({ summary }: { summary: ReviewSummaryOut }) {
  if (summary.total_reviews_analyzed === 0) {
    return <p className="text-sm text-gray-500">No reviews collected yet for this product.</p>;
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-4">
        <SentimentBar summary={summary} />
        <div className="flex gap-3 text-sm">
          {Object.entries(summary.retailer_ratings).map(([retailer, rating]) => (
            <span key={retailer} className="text-gray-600">
              {formatRetailer(retailer)}: <span className="font-medium text-amber-600">★ {rating.toFixed(1)}</span>
            </span>
          ))}
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <h4 className="mb-2 text-sm font-semibold text-emerald-700">Pros</h4>
          {summary.pros.length ? (
            <div className="flex flex-wrap gap-1.5">
              {summary.pros.map((p) => (
                <Badge key={p} variant="success">
                  {p}
                </Badge>
              ))}
            </div>
          ) : (
            <p className="text-sm text-gray-400">Not enough review signal yet.</p>
          )}
        </div>
        <div>
          <h4 className="mb-2 text-sm font-semibold text-red-700">Cons</h4>
          {summary.cons.length ? (
            <div className="flex flex-wrap gap-1.5">
              {summary.cons.map((c) => (
                <Badge key={c} variant="warning">
                  {c}
                </Badge>
              ))}
            </div>
          ) : (
            <p className="text-sm text-gray-400">No common complaints found.</p>
          )}
        </div>
      </div>

      {summary.most_mentioned_features.length > 0 && (
        <div>
          <h4 className="mb-2 text-sm font-semibold text-gray-700">Most mentioned</h4>
          <div className="flex flex-wrap gap-1.5">
            {summary.most_mentioned_features.map((f) => (
              <Badge key={f} variant="info">
                {f}
              </Badge>
            ))}
          </div>
        </div>
      )}

      <div className="space-y-3">
        <h4 className="text-sm font-semibold text-gray-700">Recent reviews</h4>
        {summary.sample_reviews.slice(0, 5).map((review) => (
          <div key={review.id} className="rounded-lg border border-gray-200 p-3">
            <div className="mb-1 flex items-center justify-between text-xs text-gray-500">
              <span>
                {review.reviewer_name ?? "Anonymous"} · {formatRetailer(review.retailer)}
                {review.verified_purchase ? " · Verified purchase" : ""}
              </span>
              <span>{formatDate(review.review_date)}</span>
            </div>
            {review.review_title && <p className="font-medium text-gray-900">{review.review_title}</p>}
            {review.review_text && <p className="mt-1 text-sm text-gray-600">{review.review_text}</p>}
          </div>
        ))}
      </div>
    </div>
  );
}

function SentimentBar({ summary }: { summary: ReviewSummaryOut }) {
  const positive = summary.positive_percent ?? 0;
  const neutral = summary.neutral_percent ?? 0;
  const negative = summary.negative_percent ?? 0;

  return (
    <div className="flex-1 min-w-[220px]">
      <div className="mb-1 flex justify-between text-xs text-gray-500">
        <span>{positive.toFixed(0)}% positive</span>
        <span>{summary.total_reviews_analyzed} reviews analyzed</span>
      </div>
      <div className="flex h-2.5 w-full overflow-hidden rounded-full bg-gray-100">
        <div className="bg-emerald-500" style={{ width: `${positive}%` }} />
        <div className="bg-gray-300" style={{ width: `${neutral}%` }} />
        <div className="bg-red-400" style={{ width: `${negative}%` }} />
      </div>
    </div>
  );
}
