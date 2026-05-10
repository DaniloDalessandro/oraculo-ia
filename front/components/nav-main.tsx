"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import {
  SidebarGroup,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar"

export function NavMain({
  items,
}: {
  items: {
    title: string
    url: string
    icon?: React.ReactNode
    items?: { title: string; url: string }[]
  }[]
}) {
  const pathname = usePathname()

  return (
    <SidebarGroup>
      <SidebarGroupLabel className="text-[11px] font-medium text-white/25 tracking-widest uppercase px-2 mb-1">
        Menu
      </SidebarGroupLabel>
      <SidebarMenu>
        {items.map((item) => {
          const isActive = pathname === item.url
          return (
            <SidebarMenuItem key={item.title}>
              <SidebarMenuButton
                asChild
                isActive={isActive}
                tooltip={item.title}
                className={
                  isActive
                    ? "bg-[#0070d1]/15 text-white [&>svg]:text-[#0070d1]"
                    : "text-white/60 hover:text-white hover:bg-white/5 [&>svg]:text-white/40"
                }
              >
                <Link href={item.url} className="flex items-center gap-2.5">
                  {item.icon}
                  <span className="text-sm font-medium">{item.title}</span>
                  {isActive && (
                    <span className="ml-auto w-1 h-4 rounded-full bg-[#0070d1]" />
                  )}
                </Link>
              </SidebarMenuButton>
            </SidebarMenuItem>
          )
        })}
      </SidebarMenu>
    </SidebarGroup>
  )
}
