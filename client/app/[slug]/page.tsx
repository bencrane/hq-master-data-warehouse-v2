import { notFound } from "next/navigation";
import { supabase } from "@/lib/supabase";

interface PageProps {
  params: Promise<{ slug: string }>;
}

async function getClientBySlug(slug: string) {
  const { data, error } = await supabase
    .schema("reference")
    .from("target_clients")
    .select("*")
    .eq("slug", slug)
    .single();

  if (error || !data) return null;
  return data;
}

async function getLeadsForClient(targetClientId: string) {
  const { data, error } = await supabase
    .schema("clients")
    .from("target_client_leads")
    .select("*")
    .eq("target_client_id", targetClientId)
    .order("projected_at", { ascending: false })
    .limit(100);

  if (error) {
    console.error("Error fetching leads:", error);
    return [];
  }
  return data || [];
}

export default async function ClientDashboard({ params }: PageProps) {
  const { slug } = await params;
  const client = await getClientBySlug(slug);

  if (!client) {
    notFound();
  }

  const leads = await getLeadsForClient(client.id);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      <header className="border-b border-slate-700/50 bg-slate-900/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-6 py-5">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-white tracking-tight">{client.company_name}</h1>
              <p className="text-slate-400 text-sm mt-0.5">{client.domain}</p>
            </div>
            <div className="text-right">
              <p className="text-4xl font-bold text-emerald-400">{leads.length}</p>
              <p className="text-slate-400 text-sm">Matched Leads</p>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-8">
        {leads.length === 0 ? (
          <div className="text-center py-20">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-slate-800 flex items-center justify-center">
              <svg className="w-8 h-8 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
              </svg>
            </div>
            <h2 className="text-xl font-semibold text-white mb-2">No leads yet</h2>
            <p className="text-slate-400">Run the projection to generate matches.</p>
          </div>
        ) : (
          <div className="grid gap-3">
            {leads.map((lead) => (
              <div
                key={lead.id}
                className="bg-slate-800/40 border border-slate-700/50 rounded-xl p-5 hover:bg-slate-800/60 transition-colors"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 mb-1">
                      {lead.linkedin_url ? (
                        <a
                          href={lead.linkedin_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-lg font-semibold text-white hover:text-blue-400 transition-colors truncate"
                        >
                          {lead.full_name}
                        </a>
                      ) : (
                        <span className="text-lg font-semibold text-white truncate">{lead.full_name}</span>
                      )}
                      {lead.worked_at_customer_company_name && (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-500/15 text-amber-400 border border-amber-500/25 whitespace-nowrap">
                          ✦ {lead.worked_at_customer_company_name} alum
                        </span>
                      )}
                    </div>
                    <p className="text-slate-300 text-sm">{lead.title || "No title"}</p>
                    <p className="text-slate-500 text-sm mt-1">
                      {lead.company_name}{lead.location_name && ` · ${lead.location_name}`}
                    </p>
                  </div>
                  {lead.linkedin_url && (
                    <a
                      href={lead.linkedin_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex-shrink-0 p-2 rounded-lg bg-slate-700/50 hover:bg-blue-600 text-slate-400 hover:text-white transition-colors"
                      aria-label="View LinkedIn profile"
                    >
                      <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>
                      </svg>
                    </a>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}

