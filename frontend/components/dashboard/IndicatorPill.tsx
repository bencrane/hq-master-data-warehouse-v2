import React from "react"
import { cn } from "@/lib/utils"

export type IndicatorType = "New in Role" | "Recently Funded" | "Worked at Customer" | "Custom"

interface IndicatorPillProps {
    type: IndicatorType
    label?: string
    className?: string
}

const styles: Record<IndicatorType, string> = {
    "New in Role": "bg-emerald-500/15 text-emerald-400 border border-emerald-500/20",
    "Recently Funded": "bg-purple-500/15 text-purple-400 border border-purple-500/20",
    "Worked at Customer": "bg-blue-500/15 text-blue-400 border border-blue-500/20",
    "Custom": "bg-gray-500/15 text-gray-400 border border-gray-500/20",
}

export function IndicatorPill({ type, label, className }: IndicatorPillProps) {
    const finalLabel = label || type;
    const style = styles[type] || styles["Custom"];

    return (
        <span className={cn(
            "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium transition-colors cursor-default select-none",
            style,
            className
        )}>
            {finalLabel}
        </span>
    )
}
