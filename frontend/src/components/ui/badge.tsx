import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-[var(--accent-primary)] focus:ring-offset-2",
  {
    variants: {
      variant: {
        default: "border-transparent bg-[var(--accent-primary)] text-white",
        secondary: "border-transparent bg-[var(--surface-tertiary)] text-[var(--text-secondary)]",
        destructive: "border-transparent bg-[var(--status-error-bg)] text-[var(--status-error)]",
        success: "border-transparent bg-[var(--status-success-bg)] text-[var(--status-success)]",
        warning: "border-transparent bg-[var(--status-warning-bg)] text-[var(--status-warning)]",
        info: "border-transparent bg-[var(--status-info-bg)] text-[var(--status-info)]",
        outline: "text-[var(--text-primary)] border-[var(--border-default)]",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />
}

export { Badge, badgeVariants }
