import * as React from "react"
import { cn } from "../../lib/utils"

const Badge = React.forwardRef(({ className, variant = "default", ...props }, ref) => {
  const variantStyles = {
    default: "bg-teal-700 text-white hover:bg-teal-600",
    secondary: "bg-gray-100 text-gray-900 hover:bg-gray-200",
    destructive: "bg-red-500 text-white hover:bg-red-600",
    outline: "text-gray-900 border border-gray-200",
  }

  return (
    <div
      ref={ref}
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-2",
        variantStyles[variant],
        className,
      )}
      {...props}
    />
  )
})
Badge.displayName = "Badge"

export { Badge }
