

export interface TargetClient {
    id: string;
    domain: string;
    company_name: string;
    created_at: string;
    updated_at: string;
    company_linkedin_url: string | null;
}

export interface Lead {
    id: string; // Assuming standard UUID
    person_full_name: string | null;
    company_name: string | null;
    person_title: string | null;
    company_industry: string | null;
    company_size: string | null;
    // company_employee_count might be an alternative, will check both or use one if confirmed. 
    // User said "company_size or company_employee_count". Let's assume company_size for now based on sample.

    // Indicators
    is_worked_at_customer?: boolean;

    // Fields from previous version that don't exist
    // email, funding_*, etc. removed

    target_client_id?: string;
}
