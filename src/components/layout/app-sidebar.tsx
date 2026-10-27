"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  Earth,
  FileText,
  Globe,
  Layers,
  PanelLeftClose,
  PanelLeftOpen,
  Settings,
  Waypoints,
  type LucideIcon,
} from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

type NavItem = {
  title: string;
  icon: LucideIcon;
  href: string;
};

const workspaces: NavItem[] = [
  { title: "Browser", href: "/browser", icon: Globe },
  { title: "Graph", href: "/graph", icon: Waypoints },
  { title: "Gaia", href: "/", icon: Earth },
  { title: "Object Explorer", href: "/object-explorer", icon: Layers },
  { title: "Dossier", href: "/dossier", icon: FileText },
];

const utilities: NavItem[] = [
  { title: "Settings", href: "/settings", icon: Settings },
  { title: "System Status", href: "/system-status", icon: Activity },
];

const row = cn(
  "flex h-8 w-full items-center gap-2 rounded-md px-2 text-xs font-medium outline-none",
  "transition-colors focus-visible:ring-2 focus-visible:ring-ring/50",
);

function isActive(pathname: string, href: string) {
  return href === "/" ? pathname === "/" : pathname === href;
}

function SidebarRow({
  title,
  icon: Icon,
  href,
  onClick,
  collapsed,
  active = false,
}: Omit<NavItem, "href"> & {
  href?: string;
  onClick?: () => void;
  collapsed: boolean;
  active?: boolean;
}) {
  const className = cn(
    row,
    active
      ? "bg-blue-50 text-blue-700"
      : "text-muted-foreground hover:bg-muted hover:text-foreground",
    collapsed && "justify-center px-0",
  );
  const content = (
    <>
      <Icon className="size-4 shrink-0" aria-hidden />
      {!collapsed && <span className="truncate">{title}</span>}
    </>
  );

  return (
    <Tooltip disabled={!collapsed}>
      <TooltipTrigger
        render={
          href ? (
            <Link
              href={href}
              aria-label={title}
              aria-current={active ? "page" : undefined}
              className={className}
            >
              {content}
            </Link>
          ) : (
            <button
              type="button"
              aria-label={title}
              onClick={onClick}
              className={className}
            >
              {content}
            </button>
          )
        }
      />
      <TooltipContent side="right" sideOffset={8}>
        {title}
      </TooltipContent>
    </Tooltip>
  );
}

export function AppSidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const pathname = usePathname();

  return (
    <TooltipProvider>
      <aside
        className={cn(
          "flex h-full shrink-0 flex-col border-r border-border bg-sidebar transition-[width] duration-150",
          collapsed ? "w-14" : "w-60",
        )}
      >
        <nav
          aria-label="Workspaces"
          className="flex min-h-0 flex-1 flex-col gap-1 overflow-y-auto p-2"
        >
          {workspaces.map((item) => (
            <SidebarRow
              key={item.href}
              {...item}
              collapsed={collapsed}
              active={isActive(pathname, item.href)}
            />
          ))}
        </nav>

        <div className="flex shrink-0 flex-col gap-1 border-t border-border p-2">
          {utilities.map((item) => (
            <SidebarRow
              key={item.href}
              {...item}
              collapsed={collapsed}
              active={isActive(pathname, item.href)}
            />
          ))}
          <SidebarRow
            title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            icon={collapsed ? PanelLeftOpen : PanelLeftClose}
            collapsed={collapsed}
            onClick={() => setCollapsed((value) => !value)}
          />
        </div>
      </aside>
    </TooltipProvider>
  );
}
