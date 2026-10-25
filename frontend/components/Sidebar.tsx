"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import {
  Activity, BarChart3, BookOpen, Bot, FlaskConical, Lightbulb, LineChart, Megaphone, Menu, TrendingUp, Users, X,
} from "lucide-react";

const NAV = [
  { href: "/", label: "Overview", icon: BarChart3 },
  { href: "/sales", label: "Sales Analysis", icon: LineChart },
  { href: "/forecast", label: "Demand Forecast", icon: TrendingUp },
  { href: "/campaigns", label: "Campaign Analysis", icon: Megaphone },
  { href: "/segments", label: "Customer Segments", icon: Users },
  { href: "/anomalies", label: "Anomalies", icon: Activity },
  { href: "/statistics", label: "Statistics Lab", icon: FlaskConical },
  { href: "/ai-analyst", label: "AI Analyst", icon: Bot },
  { href: "/insights", label: "Insights", icon: Lightbulb },
  { href: "/methodology", label: "Methodology", icon: BookOpen },
];

export default function Sidebar() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  return (
    <>
      <div className="flex items-center justify-between border-b border-slate-200 bg-white px-4 py-3 lg:hidden">
        <span className="flex items-center gap-2 font-semibold text-slate-900">
          <Image src="/mil-mark.png" alt="" width={28} height={28} className="rounded-md" priority />
          Market Intelligence Lab
        </span>
        <button
          type="button"
          aria-label={open ? "Close navigation" : "Open navigation"}
          aria-expanded={open}
          onClick={() => setOpen(!open)}
          className="rounded p-1 text-slate-700 hover:bg-slate-100"
        >
          {open ? <X size={20} /> : <Menu size={20} />}
        </button>
      </div>
      <nav
        aria-label="Main"
        className={`${open ? "block" : "hidden"} border-b border-slate-200 bg-white lg:sticky lg:top-0 lg:flex lg:flex-col lg:h-screen lg:overflow-y-auto lg:w-60 lg:shrink-0 lg:border-b-0 lg:border-r`}
      >
        <div className="hidden items-center gap-2.5 px-4 py-5 lg:flex">
          <Image src="/mil-mark.png" alt="" width={32} height={32} className="shrink-0 rounded-lg" priority />
          <div>
            <p className="text-sm font-semibold leading-tight text-slate-900">Market Intelligence Lab</p>
            <p className="mt-0.5 text-xs text-slate-500">Student data science case study</p>
          </div>
        </div>
        <ul className="space-y-0.5 px-3 pb-4">
          {NAV.map(({ href, label, icon: Icon }) => {
            const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
            return (
              <li key={href}>
                <Link
                  href={href}
                  onClick={() => setOpen(false)}
                  aria-current={active ? "page" : undefined}
                  className={`flex items-center gap-2.5 rounded-md px-3 py-2 text-sm ${
                    active ? "bg-slate-900 text-white" : "text-slate-700 hover:bg-slate-100"
                  }`}
                >
                  <Icon size={16} aria-hidden="true" />
                  {label}
                </Link>
              </li>
            );
          })}
        </ul>
        <div className="border-t border-slate-200 px-5 py-4 text-[11px] leading-relaxed text-slate-500 lg:mt-auto">
          <p>A Data Science portfolio project by Shahil</p>
          <p className="mt-1">Data: UCI Online Retail II (CC BY 4.0) plus clearly labelled synthetic fields.</p>
        </div>
      </nav>
    </>
  );
}
