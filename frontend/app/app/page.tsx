import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Navbar } from "@/components/layout/navbar";

export default function AppPage() {
  return (
    <div className="min-h-screen bg-zinc-950">
      <Navbar />
      <main className="mx-auto max-w-4xl px-6 py-16 text-center">
        <h1 className="mb-4 text-3xl font-bold text-zinc-100">Decision Laboratory</h1>
        <p className="mb-8 text-zinc-500">Start a new scenario to run autonomous agent analysis.</p>
        <div className="flex justify-center gap-4">
          <Link href="/app/new">
            <Button size="lg">New scenario</Button>
          </Link>
          <Link href="/app/new?demo=true">
            <Button variant="secondary" size="lg">Run demo</Button>
          </Link>
        </div>
      </main>
    </div>
  );
}
