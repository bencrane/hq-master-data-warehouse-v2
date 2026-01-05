'use server';

import { TargetClient } from "@/types";

const MODAL_ENDPOINT = "https://bencrane--hq-master-data-ingest-generate-target-client-icp.modal.run";

export interface ICPResult {
    target_client_id: string;
    company_name: string;
    success: boolean;
    company_criteria?: {
        industries: string[];
        employee_count_min: number | null;
        employee_count_max: number | null;
        size: string[];
        countries: string[];
        founded_min: number | null;
        founded_max: number | null;
    };
    person_criteria?: {
        title_contains_any: string[];
        title_contains_all: string[];
    };
    error?: string;
}

export async function generateICPForClients(clients: TargetClient[]): Promise<ICPResult[]> {
    const results: ICPResult[] = [];

    for (const client of clients) {
        try {
            const response = await fetch(MODAL_ENDPOINT, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    target_client_id: client.id,
                    company_name: client.company_name,
                    domain: client.domain,
                    company_linkedin_url: client.company_linkedin_url,
                }),
            });

            const data = await response.json();
            results.push({
                target_client_id: data.target_client_id || client.id,
                company_name: client.company_name,
                success: data.success,
                company_criteria: data.company_criteria,
                person_criteria: data.person_criteria,
                error: data.error,
            });
        } catch (error) {
            results.push({
                target_client_id: client.id,
                company_name: client.company_name,
                success: false,
                error: error instanceof Error ? error.message : 'Unknown error',
            });
        }
    }

    return results;
}
