import { notFound } from "next/navigation";
import { supabase } from "@/lib/supabase";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

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
      <header className="border-b border-slate-700 bg-slate-900/50 backdrop-blur-sm">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-white">{client.company_name}</h1>
              <p className="text-slate-400 text-sm">{client.domain}</p>
            </div>
            <div className="text-right">
              <p className="text-3xl font-bold text-emerald-400">{leads.length}</p>
              <p className="text-slate-400 text-sm">Matched Leads</p>
            </div>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-6 py-8">
        <Card className="bg-slate-800/50 border-slate-700">
          <CardHeader>
            <CardTitle className="text-white">Lead Matches</CardTitle>
          </CardHeader>
          <CardContent>
            {leads.length === 0 ? (
              <p className="text-slate-400 text-center py-8">
                No leads found. Run the projection to generate matches.
              </p>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow className="border-slate-700">
                      <TableHead className="text-slate-300">Name</TableHead>
                      <TableHead className="text-slate-300">Title</TableHead>
                      <TableHead className="text-slate-300">Company</TableHead>
                      <TableHead className="text-slate-300">Location</TableHead>
                      <TableHead className="text-slate-300">Alumni</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {leads.map((lead) => (
                      <TableRow key={lead.id} className="border-slate-700 hover:bg-slate-700/50">
                        <TableCell>
                          {lead.linkedin_url ? (
                            <a
                              href={lead.linkedin_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-blue-400 hover:underline font-medium"
                            >
                              {lead.full_name}
                            </a>
                          ) : (
                            <span className="text-white font-medium">{lead.full_name}</span>
                          )}
                        </TableCell>
                        <TableCell className="text-slate-300">{lead.title || "-"}</TableCell>
                        <TableCell className="text-slate-300">{lead.company_name || "-"}</TableCell>
                        <TableCell className="text-slate-400">{lead.location_name || "-"}</TableCell>
                        <TableCell>
                          {lead.worked_at_customer_company_name ? (
                            <span className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-amber-500/20 text-amber-400 border border-amber-500/30">
                              {lead.worked_at_customer_company_name}
                            </span>
                          ) : (
                            <span className="text-slate-500">-</span>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>
      </main>
    </div>
  );
}

