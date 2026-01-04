
import Link from "next/link";
import { Button } from "@/components/ui/button";

export function Navbar() {
    return (
        <nav className="border-b bg-background">
            <div className="flex h-16 items-center px-4 md:px-6 container mx-auto">
                <Link href="/" className="font-bold text-lg mr-6">
                    HQ Data
                </Link>
                <div className="flex items-center space-x-4 lg:space-x-6 mx-auto">
                    <Link
                        href="/"
                        className="text-sm font-medium transition-colors hover:text-primary"
                    >
                        Dashboard
                    </Link>
                    <Link
                        href="/bullseye"
                        className="text-sm font-medium transition-colors hover:text-primary"
                    >
                        Bullseye
                    </Link>
                    <Link
                        href="/target-clients"
                        className="text-sm font-medium text-muted-foreground transition-colors hover:text-primary"
                    >
                        Target Clients
                    </Link>
                    <Link
                        href="#"
                        className="text-sm font-medium text-muted-foreground transition-colors hover:text-primary"
                    >
                        Settings
                    </Link>

                </div>
                <div className="ml-auto flex items-center space-x-4">
                    <Button variant="outline" size="sm">
                        Log in
                    </Button>
                    <Button size="sm">Sign up</Button>
                </div>
            </div>
        </nav>
    );
}
