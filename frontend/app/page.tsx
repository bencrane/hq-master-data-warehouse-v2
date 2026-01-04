import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function Home() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-muted/40 p-10">
      <Card className="w-[350px]">
        <CardHeader>
          <CardTitle>Project Initialized</CardTitle>
          <CardDescription>
            Next.js 14 + Tailwind + Shadcn/ui
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="mb-4 text-sm text-muted-foreground">
            The frontend setup is complete. You can now start building your application.
          </p>
          <Button className="w-full">Get Started</Button>
        </CardContent>
      </Card>
    </div>
  );
}
