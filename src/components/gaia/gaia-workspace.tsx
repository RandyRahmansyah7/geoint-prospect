"use client";

import { useState } from "react";
import { ChevronRight } from "lucide-react";
import { MapCanvas } from "@/components/gaia/map-canvas";
import { StatusBar } from "@/components/gaia/status-bar";
import { ToolRail } from "@/components/gaia/tool-rail";
import { WorkspacePanel, type PanelTab } from "@/components/gaia/workspace-panel";

export function GaiaWorkspace() {
  const [tab, setTab] = useState<PanelTab>("layers");
  const [panelOpen, setPanelOpen] = useState(true);

  return (
    <div className="flex h-full flex-col">
      <div className="flex min-h-0 flex-1">
        {panelOpen ? (
          <WorkspacePanel
            tab={tab}
            onTabChange={setTab}
            onCollapse={() => setPanelOpen(false)}
          />
        ) : (
          <button
            type="button"
            onClick={() => setPanelOpen(true)}
            aria-label="Expand panel"
            className="flex h-full w-6 shrink-0 justify-center border-r border-border bg-sidebar pt-2 text-muted-foreground outline-none hover:text-foreground focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring/50"
          >
            <ChevronRight className="size-3.5" aria-hidden />
          </button>
        )}

        <MapCanvas />
        <ToolRail />
      </div>

      <StatusBar />
    </div>
  );
}
