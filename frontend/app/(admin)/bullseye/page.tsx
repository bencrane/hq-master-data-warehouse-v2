import { getTargetClients } from "@/app/(admin)/actions/get-target-clients";
import { BullseyeView } from "@/components/dashboard/BullseyeView";

export default async function BullseyePage() {
    const clients = await getTargetClients();

    return (
        <div className="h-[calc(100vh-65px)] bg-background">
            <BullseyeView initialClients={clients} />
        </div>
    );
}
