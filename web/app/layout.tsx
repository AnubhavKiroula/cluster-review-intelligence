import type { Metadata } from "next";
import "./globals.css";
import Nav from "@/components/Nav";
import { DataProvider } from "@/lib/data";

export const metadata: Metadata = {
  title: "Cluster Review Intelligence",
  description:
    "Cluster-level review analytics for Uttarakhand tourism: am I behind my cluster, since when, and is it just me or the whole market?",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <DataProvider>
          <div className="layout">
            <Nav />
            <main className="main">{children}</main>
          </div>
        </DataProvider>
      </body>
    </html>
  );
}
