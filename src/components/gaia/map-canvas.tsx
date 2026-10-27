import { Crosshair, Hexagon, MapPin, MousePointer2, Ruler } from "lucide-react";

const tools = [
  { label: "Select", icon: MousePointer2 },
  { label: "Draw polygon", icon: Hexagon },
  { label: "Draw point", icon: MapPin },
  { label: "Measure distance", icon: Ruler },
  { label: "Center on selection", icon: Crosshair },
];

export function MapCanvas() {
  return (
    <div className="relative min-w-0 flex-1 bg-muted/40 bg-[radial-gradient(var(--color-border)_1px,transparent_1px)] bg-[size:16px_16px]">
      <div
        role="toolbar"
        aria-label="Map tools"
        aria-disabled="true"
        className="absolute top-2 left-2 flex items-center gap-0.5 rounded-md border border-border bg-background/95 p-0.5 shadow-xs"
      >
        {tools.map(({ label, icon: Icon }) => (
          <button
            key={label}
            type="button"
            disabled
            title={label}
            aria-label={label}
            className="flex size-7 items-center justify-center rounded-sm text-muted-foreground disabled:cursor-not-allowed disabled:opacity-60"
          >
            <Icon className="size-3.5" aria-hidden />
          </button>
        ))}
      </div>

      <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center gap-1 px-4 text-center">
        <p className="text-xs font-medium text-muted-foreground">No basemap loaded</p>
        <p className="text-[11px] text-muted-foreground/70">
          MapLibre GL and PMTiles arrive with the Gaia map issue.
        </p>
      </div>
    </div>
  );
}
