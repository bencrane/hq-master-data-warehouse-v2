'use client';

import { useState, useEffect } from "react";
import { TargetClient, Lead } from "@/types";
import { getLeads } from "@/app/actions/get-leads";
import { cn } from "@/lib/utils";
import { LeadsTable } from "./LeadsTable";
import { Input } from "@/components/ui/input";
import { PremiumButton } from "@/components/ui/premium-button";
import { Search, Filter, Columns } from "lucide-react";

interface BullseyeViewProps {
    initialClients: TargetClient[];
}

export function BullseyeView({ initialClients }: BullseyeViewProps) {
    const [selectedClientId, setSelectedClientId] = useState<string | null>(initialClients[0]?.id || null);
    const [leads, setLeads] = useState<Lead[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [clientSearch, setClientSearch] = useState("");

    const filteredClients = initialClients.filter(c =>
        c.company_name.toLowerCase().includes(clientSearch.toLowerCase())
    );

    useEffect(() => {
        if (!selectedClientId) return;

        async function fetchLeads() {
            setIsLoading(true);
            try {
                const data = await getLeads(selectedClientId!);
                setLeads(data);
            } catch (error) {
                console.error("Failed to fetch leads", error);
            } finally {
                setIsLoading(false);
            }
        }

        fetchLeads();
    }, [selectedClientId]);

    return (
        <div className="flex h-full">
            {/* Sidebar for Clients */}
            <aside className="w-64 border-r bg-sidebar border-sidebar-border flex flex-col">
                <div className="p-4 border-b border-sidebar-border">
                    <h2 className="font-semibold text-sidebar-foreground mb-2">Target Clients</h2>
                    <div className="relative">
                        <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                        <Input
                            placeholder="Search clients..."
                            className="pl-8 bg-sidebar-accent/50 border-sidebar-border text-sidebar-foreground placeholder:text-muted-foreground/50 h-9"
                            value={clientSearch}
                            onChange={(e) => setClientSearch(e.target.value)}
                        />
                    </div>
                </div>
                <div className="flex-1 overflow-y-auto p-2 space-y-1">
                    {filteredClients.map(client => (
                        <button
                            key={client.id}
                            onClick={() => setSelectedClientId(client.id)}
                            className={cn(
                                "w-full text-left px-3 py-2 rounded-md text-sm transition-colors",
                                selectedClientId === client.id
                                    ? "bg-sidebar-primary text-sidebar-primary-foreground font-medium"
                                    : "text-sidebar-foreground hover:bg-sidebar-accent"
                            )}
                        >
                            {client.company_name}
                        </button>
                    ))}
                    {filteredClients.length === 0 && (
                        <div className="text-center py-4 text-xs text-muted-foreground">
                            No clients found
                        </div>
                    )}
                </div>
            </aside>

            {/* Main Content */}
            <main className="flex-1 flex flex-col bg-background min-w-0">
                <div className="h-14 border-b flex items-center justify-between px-6 bg-background/50 backdrop-blur-sm">
                    <div className="flex items-center gap-2">
                        <h1 className="text-lg font-semibold">
                            {initialClients.find(c => c.id === selectedClientId)?.company_name || "Select a Client"}
                        </h1>
                        <span className="text-muted-foreground text-sm font-normal">
                            {leads.length} leads found
                        </span>
                    </div>
                    <div className="flex items-center gap-2">
                        <PremiumButton variant="premium-ghost" size="sm" className="h-8 gap-2 group">
                            <Filter className="w-4 h-4 text-muted-foreground group-hover:text-foreground transition-colors" />
                            <span className="text-muted-foreground group-hover:text-foreground transition-colors">Filters</span>
                        </PremiumButton>
                        <PremiumButton variant="premium-ghost" size="sm" className="h-8 gap-2 group">
                            <Columns className="w-4 h-4 text-muted-foreground group-hover:text-foreground transition-colors" />
                            <span className="text-muted-foreground group-hover:text-foreground transition-colors">Columns</span>
                        </PremiumButton>
                    </div>
                </div>

                <div className="flex-1 overflow-auto p-0">
                    <LeadsTable leads={leads} isLoading={isLoading} />
                </div>
            </main>
        </div>
    );
}
