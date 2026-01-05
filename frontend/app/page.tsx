import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function AdminHome() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-muted/40 p-10">
      <Card className="w-[350px]">
        <CardHeader>
          <CardTitle>Admin Dashboard</CardTitle>
          <CardDescription>
            HQ Master Data Warehouse
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="mb-4 text-sm text-muted-foreground">
            Manage target clients, generate ICPs, and run projections.
          </p>
          <Button className="w-full" asChild>
            <a href="/target-clients">View Target Clients</a>
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}

