"use client";

import { useEffect, useState } from "react";

export function StatusBar() {
  const [time, setTime] = useState<string | null>(null);

  useEffect(() => {
    const tick = () => setTime(new Date().toLocaleTimeString());
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="flex h-7 shrink-0 items-center gap-3 border-t border-border bg-sidebar px-2 text-[11px] text-muted-foreground">
      <span className="flex items-center gap-1.5">
        <span className="size-1.5 rounded-full bg-amber-500" aria-hidden />
        Engine: offline
      </span>
      <span>Basemap: none</span>
      <span>Overlays: 0</span>

      <span className="ml-auto flex items-center gap-3">
        <span className="flex items-center gap-0.5" role="group" aria-label="Coordinate format">
          {["DD", "DMS"].map((format) => (
            <button
              key={format}
              type="button"
              disabled
              className="rounded-sm px-1.5 py-0.5 text-[11px] disabled:cursor-not-allowed disabled:opacity-60"
            >
              {format}
            </button>
          ))}
        </span>
        <span className="tabular-nums">{time ?? "--:--:--"}</span>
      </span>
    </div>
  );
}
