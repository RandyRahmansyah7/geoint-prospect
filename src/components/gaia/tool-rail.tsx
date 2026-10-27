import {
  ChartColumn,
  ChartGantt,
  CircleHelp,
  Funnel,
  ListTree,
  MousePointer2,
  Ruler,
} from "lucide-react";

const rail = [
  { label: "Legend", icon: ListTree },
  { label: "Selection", icon: MousePointer2 },
  { label: "Histogram", icon: ChartColumn },
  { label: "Timeline", icon: ChartGantt },
  { label: "Filter", icon: Funnel },
  { label: "Measure", icon: Ruler },
  { label: "Help", icon: CircleHelp },
];

export function ToolRail() {
  return (
    <div
      role="toolbar"
      aria-orientation="vertical"
      aria-label="Panels"
      aria-disabled="true"
      className="flex h-full w-9 shrink-0 flex-col items-center gap-0.5 border-l border-border bg-sidebar py-1"
    >
      {rail.map(({ label, icon: Icon }) => (
        <button
          key={label}
          type="button"
          disabled
          title={label}
          aria-label={label}
          className="flex size-7 items-center justify-center rounded-md text-muted-foreground disabled:cursor-not-allowed disabled:opacity-60"
        >
          <Icon className="size-4" aria-hidden />
        </button>
      ))}
    </div>
  );
}
