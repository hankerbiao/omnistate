import { Toaster as Sonner } from "sonner"
import { useTheme } from "next-themes"

type ToasterProps = React.ComponentProps<typeof Sonner>

const Toaster = ({ ...props }: ToasterProps) => {
  const { theme = "system" } = useTheme()

  return (
    <Sonner
      theme={theme as ToasterProps["theme"]}
      className="toaster group"
      toastOptions={{
        classNames: {
          toast:
            "group toast group-[.toaster]:bg-[var(--surface-elevated)] group-[.toaster]:text-[var(--text-primary)] group-[.toaster]:border-[var(--border-subtle)] group-[.toaster]:shadow-lg",
          description: "group-[.toast]:text-[var(--text-secondary)]",
          actionButton:
            "group-[.toast]:bg-[var(--accent-primary)] group-[.toast]:text-white",
          cancelButton:
            "group-[.toast]:bg-[var(--surface-tertiary)] group-[.toast]:text-[var(--text-secondary)]",
        },
      }}
      {...props}
    />
  )
}

export { Toaster }
