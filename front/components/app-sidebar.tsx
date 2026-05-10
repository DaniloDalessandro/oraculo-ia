"use client"

import * as React from "react"
import { NavMain } from "@/components/nav-main"
import { NavUser } from "@/components/nav-user"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
} from "@/components/ui/sidebar"
import { HugeiconsIcon } from "@hugeicons/react"
import { GridViewIcon, DatabaseIcon, RoboticIcon, BookOpen01Icon } from "@hugeicons/core-free-icons"

const data = {
  user: {
    name: "Usuário",
    email: "",
    avatar: "",
  },
  navMain: [
    {
      title: "Dashboard",
      url: "/dashboard",
      icon: <HugeiconsIcon icon={GridViewIcon} strokeWidth={1.5} />,
      items: [],
    },
    {
      title: "Dados",
      url: "/dashboard/dados",
      icon: <HugeiconsIcon icon={DatabaseIcon} strokeWidth={1.5} />,
      items: [],
    },
    {
      title: "ITA",
      url: "/dashboard/ita",
      icon: <HugeiconsIcon icon={RoboticIcon} strokeWidth={1.5} />,
      items: [],
    },
    {
      title: "Conhecimento",
      url: "/dashboard/conhecimento",
      icon: <HugeiconsIcon icon={BookOpen01Icon} strokeWidth={1.5} />,
      items: [],
    },
  ],
}

export function AppSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
  return (
    <Sidebar collapsible="icon" {...props}>
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" asChild>
              <a href="/dashboard">
                {/* Logo mark */}
                <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-[#0070d1]">
                  <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                    <circle cx="7" cy="7" r="5.5" stroke="white" strokeWidth="1.5" />
                    <circle cx="7" cy="7" r="2" fill="white" />
                  </svg>
                </div>
                <div className="grid flex-1 text-left text-sm leading-tight">
                  <span className="truncate font-semibold text-white">Oráculo</span>
                  <span className="truncate text-[11px] text-white/40">v1.0.0</span>
                </div>
              </a>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>

      <SidebarContent>
        <NavMain items={data.navMain} />
      </SidebarContent>

      <SidebarFooter>
        <NavUser user={data.user} />
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  )
}
