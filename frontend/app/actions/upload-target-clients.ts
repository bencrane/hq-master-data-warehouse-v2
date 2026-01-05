'use server';

import { supabase } from "@/lib/supabase";

export interface TargetClientRow {
  company_name: string;
  domain: string;
  company_linkedin_url?: string;
  slug?: string;
}

export interface UploadResult {
  success: boolean;
  inserted: number;
  errors: string[];
}

function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/(^-|-$)/g, '');
}

export async function uploadTargetClients(rows: TargetClientRow[]): Promise<UploadResult> {
  const errors: string[] = [];
  let inserted = 0;

  for (const row of rows) {
    // Validate required fields
    if (!row.company_name?.trim()) {
      errors.push(`Missing company_name for row`);
      continue;
    }
    if (!row.domain?.trim()) {
      errors.push(`Missing domain for ${row.company_name}`);
      continue;
    }

    // Auto-generate slug if not provided
    const slug = row.slug?.trim() || slugify(row.company_name);

    try {
      const { error } = await supabase
        .schema("reference")
        .from("target_clients")
        .insert({
          company_name: row.company_name.trim(),
          domain: row.domain.trim().toLowerCase(),
          company_linkedin_url: row.company_linkedin_url?.trim() || null,
          slug: slug,
        });

      if (error) {
        if (error.code === '23505') {
          errors.push(`Duplicate: ${row.company_name} (slug or domain already exists)`);
        } else {
          errors.push(`Failed to insert ${row.company_name}: ${error.message}`);
        }
      } else {
        inserted++;
      }
    } catch (err) {
      errors.push(`Error inserting ${row.company_name}: ${err}`);
    }
  }

  return {
    success: errors.length === 0,
    inserted,
    errors,
  };
}

