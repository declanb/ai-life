"use client";

import { usePathname } from "next/navigation";

import { Separator } from "@/components/ui/separator";
import { SidebarTrigger } from "@/components/ui/sidebar";

const TITLES: Record<string, string> = {
  "/dashboard": "Overview",
  "/dashboard/transit": "Transit",
  "/dashboard/travel": "Travel",
  "/dashboard/property": "Property",
  "/dashboard/photos": "Photos",
  "/dashboard/vercel": "Vercel",
};

function titleFor(pathname: string): string {
  if (TITLES[pathname]) return TITLES[pathname]!;
  const match = Object.keys(TITLES)
    .filter((p) => p !== "/dashboard")
    .find((p) => pathname.startsWith(`${p}/`));
  if (match) return TITLES[match]!;
  return "Dashboard";
}

export function SiteHeader() {
  const pathname = usePathname();
  const title = titleFor(pathname);

  return (
    <header className="flex h-(--header-height) shrink-0 items-center gap-2 border-b transition-[width,height] ease-linear group-has-data-[collapsible=icon]/sidebar-wrapper:h-(--header-height)">
      <div className="flex w-full items-center gap-1 px-4 lg:gap-2 lg:px-6">
        <SidebarTrigger className="-ml-1" />
        <Separator
          orientation="vertical"
          className="mx-2 h-4 data-vertical:self-auto"
        />
        <h1 className="text-base font-medium">{title}</h1>
      </div>
    </header>
  );
}
