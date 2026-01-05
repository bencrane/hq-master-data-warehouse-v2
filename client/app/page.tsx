import { supabase } from "@/lib/supabase";
import Link from "next/link";

async function getClients() {
  const { data, error } = await supabase
    .schema("reference")
    .from("target_clients")
    .select("slug, company_name")
    .order("company_name");

  if (error) return [];
  return data || [];
}

export default async function Home() {
  const clients = await getClients();

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-white mb-2">GTM Dashboard</h1>
        <p className="text-slate-400 mb-8">Select your company dashboard</p>
        
        <div className="flex flex-col gap-3">
          {clients.map((client) => (
            <Link
              key={client.slug}
              href={`/${client.slug}`}
              className="px-6 py-3 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg text-white font-medium transition-colors"
            >
              {client.company_name}
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
