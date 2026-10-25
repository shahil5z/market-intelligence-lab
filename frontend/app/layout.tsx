import type { Metadata } from "next";
import Sidebar from "@/components/Sidebar";
import "./globals.css";

export const metadata: Metadata = {
  title: "Market Intelligence Lab",
  description: "An end-to-end data science case study for understanding demand, sales performance and consumer behavior.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className="antialiased">
        <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:bg-white focus:p-2">
          Skip to content
        </a>
        <div className="lg:flex">
          <Sidebar />
          <div className="min-w-0 flex-1">
            <div className="border-b border-slate-200 bg-white px-4 py-3 sm:px-8">
              <p className="text-xs text-slate-500">
                Market Intelligence Lab · An end-to-end data science case study for understanding demand, sales performance and consumer behavior.
              </p>
            </div>
            <main id="main" className="mx-auto max-w-7xl px-4 py-6 sm:px-8">{children}</main>
            <footer className="px-4 pb-6 text-xs text-slate-500 sm:px-8">
              <p>Built as a Data Science portfolio project by Shahil.</p>
              <p className="mt-1">Data: UCI Online Retail II (CC BY 4.0) plus clearly labelled synthetic fields.</p>
            </footer>
          </div>
        </div>
      </body>
    </html>
  );
}
