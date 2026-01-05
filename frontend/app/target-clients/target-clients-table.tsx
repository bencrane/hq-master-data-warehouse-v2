'use client';

import { useState } from 'react';
import Link from 'next/link';
import { TargetClient } from '@/types';
import {
    Table, TableBody, TableCaption, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { Checkbox } from "@/components/ui/checkbox";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { format } from "date-fns";
import { generateICPForClients, ICPResult } from "@/app/actions/generate-icp";

interface TargetClientsTableProps {
    clients: TargetClient[];
}

export function TargetClientsTable({ clients }: TargetClientsTableProps) {
    const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
    const [isProcessing, setIsProcessing] = useState(false);
    const [results, setResults] = useState<ICPResult[] | null>(null);

    const handleSelectAll = (checked: boolean) => {
        setSelectedIds(checked ? new Set(clients.map((c) => c.id)) : new Set());
    };

    const handleSelectRow = (id: string, checked: boolean) => {
        const newSelected = new Set(selectedIds);
        checked ? newSelected.add(id) : newSelected.delete(id);
        setSelectedIds(newSelected);
    };

    const handleGenerateICP = async () => {
        const selectedClients = clients.filter(c => selectedIds.has(c.id));
        if (selectedClients.length === 0) return;

        setIsProcessing(true);
        setResults(null);

        try {
            const icpResults = await generateICPForClients(selectedClients);
            setResults(icpResults);
        } catch (error) {
            console.error("Error generating ICP:", error);
        } finally {
            setIsProcessing(false);
        }
    };

    return (
        <div className="space-y-6">
            <Card>
                <CardHeader className="flex flex-row items-center justify-between">
                    <CardTitle>Target Clients</CardTitle>
                    <div className="flex gap-2">
                        <Button variant="outline" asChild>
                            <Link href="/target-clients/upload">Upload CSV</Link>
                        </Button>
                        <Button 
                            disabled={selectedIds.size === 0 || isProcessing} 
                            onClick={handleGenerateICP}
                        >
                            {isProcessing ? "Generating..." : `Generate ICP (${selectedIds.size})`}
                        </Button>
                    </div>
                </CardHeader>
                <CardContent>
                    <Table>
                        <TableCaption>Select clients and click Generate ICP to create criteria using AI.</TableCaption>
                        <TableHeader>
                            <TableRow>
                                <TableHead className="w-[50px]">
                                    <Checkbox
                                        checked={clients.length > 0 && selectedIds.size === clients.length}
                                        onCheckedChange={(checked) => handleSelectAll(checked as boolean)}
                                        aria-label="Select all"
                                    />
                                </TableHead>
                                <TableHead>Company Name</TableHead>
                                <TableHead>Domain</TableHead>
                                <TableHead>LinkedIn</TableHead>
                                <TableHead className="text-right">Created At</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {clients.length === 0 ? (
                                <TableRow>
                                    <TableCell colSpan={5} className="text-center">No clients found.</TableCell>
                                </TableRow>
                            ) : (
                                clients.map((client) => (
                                    <TableRow key={client.id} data-state={selectedIds.has(client.id) ? "selected" : undefined}>
                                        <TableCell>
                                            <Checkbox
                                                checked={selectedIds.has(client.id)}
                                                onCheckedChange={(checked) => handleSelectRow(client.id, checked as boolean)}
                                                aria-label={`Select ${client.company_name}`}
                                            />
                                        </TableCell>
                                        <TableCell className="font-medium">{client.company_name}</TableCell>
                                        <TableCell>{client.domain}</TableCell>
                                        <TableCell>
                                            {client.company_linkedin_url ? (
                                                <a href={client.company_linkedin_url} target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:underline">Link</a>
                                            ) : "-"}
                                        </TableCell>
                                        <TableCell className="text-right">{format(new Date(client.created_at), 'PPP')}</TableCell>
                                    </TableRow>
                                ))
                            )}
                        </TableBody>
                    </Table>
                </CardContent>
            </Card>

            {results && (
                <Card>
                    <CardHeader><CardTitle>ICP Generation Results</CardTitle></CardHeader>
                    <CardContent>
                        <div className="space-y-4">
                            {results.map((result) => (
                                <div key={result.target_client_id} className="border rounded-lg p-4">
                                    <div className="flex items-center justify-between mb-2">
                                        <h3 className="font-semibold">{result.company_name}</h3>
                                        <span className={`px-2 py-1 rounded text-sm ${result.success ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                                            {result.success ? 'Saved to DB' : 'Failed'}
                                        </span>
                                    </div>
                                    {result.error && <p className="text-red-600 text-sm">{result.error}</p>}
                                    {result.success && result.company_criteria && (
                                        <div className="mt-2 text-sm grid grid-cols-2 gap-4">
                                            <div>
                                                <p className="font-medium text-gray-600">Company Criteria</p>
                                                <ul className="mt-1 space-y-1">
                                                    <li><span className="text-gray-500">Industries:</span> {result.company_criteria.industries.join(', ') || 'Any'}</li>
                                                    <li><span className="text-gray-500">Size:</span> {result.company_criteria.size.join(', ') || 'Any'}</li>
                                                    <li><span className="text-gray-500">Countries:</span> {result.company_criteria.countries.join(', ') || 'Any'}</li>
                                                </ul>
                                            </div>
                                            <div>
                                                <p className="font-medium text-gray-600">Person Criteria</p>
                                                <ul className="mt-1 space-y-1">
                                                    <li><span className="text-gray-500">Seniority:</span> {result.person_criteria?.title_contains_any.join(', ') || 'Any'}</li>
                                                    <li><span className="text-gray-500">Function:</span> {result.person_criteria?.title_contains_all.join(', ') || 'Any'}</li>
                                                </ul>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    </CardContent>
                </Card>
            )}
        </div>
    );
}
