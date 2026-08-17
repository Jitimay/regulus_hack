import { cn } from "@/lib/utils";

interface BadgeProps {
  children: React.ReactNode;
  variant?: "default" | "success" | "warning" | "error" | "info" | "outline";
  className?: string;
}

const variantClasses = {
  default: "bg-zinc-800 text-zinc-300 border-zinc-700",
  success: "bg-emerald-950 text-emerald-400 border-emerald-800",
  warning: "bg-amber-950 text-amber-400 border-amber-800",
  error: "bg-red-950 text-red-400 border-red-800",
  info: "bg-blue-950 text-blue-400 border-blue-800",
  outline: "bg-transparent text-zinc-400 border-zinc-600",
};

export function Badge({ children, variant = "default", className }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded border px-2 py-0.5 text-xs font-medium",
        variantClasses[variant],
        className,
      )}
    >
      {children}
    </span>
  );
}
