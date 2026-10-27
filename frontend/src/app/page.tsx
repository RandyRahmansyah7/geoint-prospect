import { Button } from "@/components/ui/button";

export default function Home() {
  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-4 p-8 text-center">
      <h1 className="text-2xl font-semibold tracking-tight">GEOINT Prospect</h1>
      <p className="max-w-md text-sm text-muted-foreground">
        Desktop shell scaffold. Analysis modules are not implemented yet.
      </p>
      <Button>Workspace ready</Button>
    </main>
  );
}
