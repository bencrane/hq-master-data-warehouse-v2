
import { getTargetClients } from "@/app/actions/get-target-clients";
import { TargetClientsTable } from "./target-clients-table";

export default async function TargetClientsPage() {
    const clients = await getTargetClients();

    return (
        <div className="container mx-auto p-10">
            <TargetClientsTable clients={clients} />
        </div>
    );
}
