"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import {
  LayoutDashboardIcon,
  BusIcon,
  PlaneIcon,
  HomeIcon,
  ImageIcon,
  ServerIcon,
  WalletIcon,
  HouseWifiIcon,
  Settings2Icon,
  CircleHelpIcon,
  SparklesIcon,
  MapPinIcon,
} from "lucide-react";

import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import { NavUser } from "@/components/nav-user";

type NavItem = {
  title: string;
  url: string;
  icon: React.ComponentType<{ className?: string }>;
  disabled?: boolean;
};

const navMain: NavItem[] = [
  { title: "Overview", url: "/dashboard", icon: LayoutDashboardIcon },
];

const navLife: NavItem[] = [
  { title: "Transit", url: "/dashboard/transit", icon: BusIcon },
  { title: "Travel", url: "/dashboard/travel", icon: PlaneIcon },
  { title: "Free Day", url: "/dashboard/free-day", icon: MapPinIcon },
  { title: "Property", url: "/dashboard/property", icon: HomeIcon },
  { title: "Photos", url: "/dashboard/photos", icon: ImageIcon },
  { title: "Smart Home", url: "/dashboard/smart-home", icon: HouseWifiIcon, disabled: true },
  { title: "Finances", url: "/dashboard/finances", icon: WalletIcon, disabled: true },
];

const navOps: NavItem[] = [
  { title: "Vercel", url: "/dashboard/vercel", icon: ServerIcon },
];

const navSecondary: NavItem[] = [
  { title: "Settings", url: "/dashboard/settings", icon: Settings2Icon, disabled: true },
  { title: "Help", url: "/dashboard/help", icon: CircleHelpIcon, disabled: true },
];

const user = {
  name: "Declan",
  email: "declan@ai-life.local",
  avatar: "/avatars/declan.jpg",
};

function NavSection({
  label,
  items,
  pathname,
}: {
  label?: string;
  items: NavItem[];
  pathname: string;
}) {
  return (
    <SidebarGroup>
      {label ? <SidebarGroupLabel>{label}</SidebarGroupLabel> : null}
      <SidebarGroupContent>
        <SidebarMenu>
          {items.map((item) => {
            const Icon = item.icon;
            const isActive =
              pathname === item.url ||
              (item.url !== "/dashboard" && pathname.startsWith(`${item.url}/`));
            return (
              <SidebarMenuItem key={item.url}>
                <SidebarMenuButton
                  isActive={isActive}
                  tooltip={item.title}
                  disabled={item.disabled}
                  render={
                    item.disabled ? (
                      <span aria-disabled="true" />
                    ) : (
                      <Link href={item.url} />
                    )
                  }
                >
                  <Icon className="size-4" />
                  <span>{item.title}</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
            );
          })}
        </SidebarMenu>
      </SidebarGroupContent>
    </SidebarGroup>
  );
}

export function AppSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
  const pathname = usePathname();

  return (
    <Sidebar collapsible="offcanvas" {...props}>
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton
              className="data-[slot=sidebar-menu-button]:p-1.5!"
              render={<Link href="/dashboard" />}
            >
              <SparklesIcon className="size-5! text-primary" />
              <span className="text-base font-semibold">AI-Life</span>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>
      <SidebarContent>
        <NavSection items={navMain} pathname={pathname} />
        <NavSection label="Life" items={navLife} pathname={pathname} />
        <NavSection label="Ops" items={navOps} pathname={pathname} />
        <NavSection items={navSecondary} pathname={pathname} />
      </SidebarContent>
      <SidebarFooter>
        <NavUser user={user} />
      </SidebarFooter>
    </Sidebar>
  );
}
