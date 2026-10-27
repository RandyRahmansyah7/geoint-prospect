export function WorkspacePlaceholder({ title }: { title: string }) {
  return (
    <section className="flex flex-col gap-1 p-4">
      <h1 className="text-sm font-medium">{title}</h1>
      <p className="text-xs text-muted-foreground">
        Workspace shell placeholder. Features arrive in a later issue.
      </p>
    </section>
  );
}
