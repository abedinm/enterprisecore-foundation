import { cn } from "@/lib/cn";

type Variant = "default" | "brand" | "success" | "warning" | "danger" | "info" | "outline";

const colors: Record<Variant, string> = {
  default:  "bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300",
  brand:    "bg-brand-500/15 text-brand-600 dark:text-brand-300",
  success:  "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400",
  warning:  "bg-amber-500/15 text-amber-700 dark:text-amber-400",
  danger:   "bg-rose-500/15 text-rose-600 dark:text-rose-400",
  info:     "bg-sky-500/15 text-sky-600 dark:text-sky-400",
  outline:  "border border-zinc-300 dark:border-zinc-700"
};

export function Badge({ className, variant = "default", ...props }: React.HTMLAttributes<HTMLSpanElement> & { variant?: Variant }) {
  return <span className={cn("inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium", colors[variant], className)} {...props} />;
}
