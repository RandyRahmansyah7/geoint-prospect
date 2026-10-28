"use client";

import {
  ChevronLeft,
  Clock,
  Database,
  Flame,
  Footprints,
  LassoSelect,
  Layers,
  Map as MapIcon,
  Route,
  Search,
  Wrench,
} from "lucide-react";
import { cn } from "@/lib/utils";

export type PanelTab = "layers" | "sources" | "tools";

const tabs = [
  { id: "layers", label: "Layers", icon: Layers },
  { id: "sources", label: "Sources", icon: Database },
  { id: "tools", label: "Tools", icon: Wrench },
] as const;

// Registered Gaia tool names only — behaviour arrives with their own issues (PRD §4.1).
const gaiaTools = [
  { name: "Track & Breadcrumbs", icon: Footprints },
  { name: "Heatmap", icon: Flame },
  { name: "Routes & Pathways", icon: Route },
  { name: "Draw & Spatial Search", icon: LassoSelect },
  { name: "Time Control", icon: Clock },
  { name: "Map Layers", icon: MapIcon },
];

function EmptyState({ text, hint }: { text: string; hint: string }) {
  return (
    <div className="flex flex-col gap-1 px-1 py-2">
      <p className="text-xs text-muted-foreground">{text}</p>
      <p className="text-[11px] text-muted-foreground/70">{hint}</p>
    </div>
  );
}

export function WorkspacePanel({
  tab,
  onTabChange,
  onCollapse,
}: {
  tab: PanelTab;
  onTabChange: (tab: PanelTab) => void;
  onCollapse: () => void;
}) {
  return (
    <aside
      aria-label="Gaia panel"
      className="flex h-full w-62 shrink-0 flex-col border-r border-border bg-sidebar"
    >
      <div className="flex h-8 shrink-0 items-stretch border-b border-border">
        {tabs.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            type="button"
            onClick={() => onTabChange(id)}
            aria-pressed={tab === id}
            className={cn(
              "flex flex-1 items-center justify-center gap-1.5 text-[11px] font-medium outline-none",
              "focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring/50",
              tab === id
                ? "bg-blue-50/70 text-blue-700"
                : "text-muted-foreground hover:bg-muted hover:text-foreground",
            )}
          >
            <Icon className="size-3.5 shrink-0" aria-hidden />
            {label}
          </button>
        ))}
        <button
          type="button"
          onClick={onCollapse}
          aria-label="Collapse panel"
          className="flex w-6 shrink-0 items-center justify-center text-muted-foreground outline-none hover:text-foreground focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring/50"
        >
          <ChevronLeft className="size-3.5" aria-hidden />
        </button>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-2">
        {tab === "layers" && (
          <div className="flex flex-col gap-2">
            <div className="relative">
              <Search
                className="pointer-events-none absolute top-1/2 left-2 size-3.5 -translate-y-1/2 text-muted-foreground"
                aria-hidden
              />
              <input
                type="search"
                disabled
                aria-label="Search layers"
                placeholder="Search layers"
                className="h-7 w-full rounded-md border border-border bg-background pr-2 pl-7 text-xs outline-none placeholder:text-muted-foreground disabled:cursor-not-allowed disabled:opacity-60"
              />
            </div>
            <EmptyState
              text="No layers yet."
              hint="Layer management arrives with the Gaia map work."
            />
          </div>
        )}

        {tab === "sources" && (
          <EmptyState
            text="No sources configured."
            hint="Source definitions live in configs/sources/."
          />
        )}

        {tab === "tools" && (
          <div className="flex flex-col">
            <p className="px-2 pb-1 text-[11px] text-muted-foreground/70">
              Registered names. Behaviour arrives with their own issues.
            </p>
            <ul aria-label="Gaia tools" className="flex flex-col">
              {gaiaTools.map(({ name, icon: Icon }) => (
                <li
                  key={name}
                  className="flex h-8 items-center gap-2 px-2 text-xs text-muted-foreground"
                >
                  <Icon className="size-4 shrink-0" aria-hidden />
                  <span className="truncate">{name}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </aside>
  );
}
