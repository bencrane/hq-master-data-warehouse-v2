'use client';

import { Lead } from "@/types";
import { IndicatorPill } from "./IndicatorPill";
import { cn } from "@/lib/utils";
import { Checkbox } from "@/components/ui/checkbox";
import { useState } from "react";

interface LeadsTableProps {
    leads: Lead[];
    isLoading: boolean;
}

export function LeadsTable({ leads, isLoading }: LeadsTableProps) {
    const [selectedRows, setSelectedRows] = useState<Set<string>>(new Set());

    const toggleRow = (id: string) => {
        const newSelected = new Set(selectedRows);
        if (newSelected.has(id)) {
            newSelected.delete(id);
        } else {
            newSelected.add(id);
        }
        setSelectedRows(newSelected);
    };

    const toggleAll = () => {
        if (selectedRows.size === leads.length) {
            setSelectedRows(new Set());
        } else {
            setSelectedRows(new Set(leads.map(l => l.id)));
        }
    };

    if (isLoading) {
        return (
            <div className="w-full h-full flex items-center justify-center text-muted-foreground">
                <div className="animate-pulse">Loading leads...</div>
            </div>
        );
    }

    if (leads.length === 0) {
        return (
            <div className="w-full h-full flex items-center justify-center text-muted-foreground">
                No leads found for this client.
            </div>
        );
    }

    return (
        <div className="w-full min-w-[1200px] text-sm">
            {/* Header */}
            <div className="flex items-center border-b bg-muted/30 text-muted-foreground font-medium sticky top-0 backdrop-blur-sm z-10">
                <div className="w-12 p-3 flex justify-center flex-none">
                    <Checkbox
                        checked={leads.length > 0 && selectedRows.size === leads.length}
                        onCheckedChange={toggleAll}
                        className="border-muted-foreground/50 data-[state=checked]:bg-primary data-[state=checked]:border-primary"
                    />
                </div>
                <div className="flex-[2] p-3 min-w-[200px]">Name</div>
                <div className="flex-1 p-3 min-w-[150px]">Company</div>
                <div className="flex-[1.5] p-3 min-w-[180px]">Title</div>
                <div className="w-[180px] p-3 flex-none">Industry</div>
                <div className="w-[140px] p-3 flex-none">Size</div>
                <div className="flex-[1.5] p-3 min-w-[200px]">Indicators</div>
            </div>

            {/* Rows */}
            <div className="divide-y divide-border/50">
                {leads.map((lead) => {
                    const isSelected = selectedRows.has(lead.id);
                    return (
                        <div
                            key={lead.id}
                            className={cn(
                                "flex items-center hover:bg-muted/30 transition-colors group",
                                isSelected && "bg-muted/40"
                            )}
                        >
                            <div className="w-12 p-3 flex justify-center flex-none">
                                <Checkbox
                                    checked={isSelected}
                                    onCheckedChange={() => toggleRow(lead.id)}
                                    className={cn(
                                        "border-muted-foreground/30 data-[state=checked]:bg-primary transition-opacity",
                                        !isSelected && "opacity-0 group-hover:opacity-100"
                                    )}
                                />
                            </div>
                            <div className="flex-[2] p-3 min-w-[200px] truncate font-medium text-foreground">
                                {lead.person_full_name}
                            </div>
                            <div className="flex-1 p-3 min-w-[150px] font-medium truncate">
                                {lead.company_name}
                            </div>
                            <div className="flex-[1.5] p-3 min-w-[180px] truncate text-muted-foreground">
                                {lead.person_title}
                            </div>
                            <div className="w-[180px] p-3 truncate text-muted-foreground flex-none">
                                {lead.company_industry}
                            </div>
                            <div className="w-[140px] p-3 text-muted-foreground text-xs flex-none truncate">
                                {lead.company_size}
                            </div>
                            <div className="flex-[1.5] p-3 min-w-[200px] flex flex-wrap gap-2">
                                {lead.is_worked_at_customer && <IndicatorPill type="Worked at Customer" />}
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
