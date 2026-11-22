import clsx from "clsx";

const VARIANTS = {
  success: "bg-emerald-50 text-emerald-700 border-emerald-200",
  info: "bg-brand-50 text-brand-700 border-brand-200",
  warning: "bg-amber-50 text-amber-700 border-amber-200",
  neutral: "bg-gray-50 text-gray-600 border-gray-200",
};

export function Badge({
  children,
  variant = "neutral",
}: {
  children: React.ReactNode;
  variant?: keyof typeof VARIANTS;
}) {
  return (
    <span
      className={clsx(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium",
        VARIANTS[variant]
      )}
    >
      {children}
    </span>
  );
}
