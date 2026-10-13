import type { Metadata, Viewport } from "next";
import { Public_Sans, Source_Serif_4 } from "next/font/google";
import "./globals.css";
import Header from "@/components/Nav";
import { SyntheticBanner } from "@/components/ui";
import { DataProvider } from "@/lib/data";

// Self-hosted at build time by next/font: the site makes no requests to Google.
// Both are SIL Open Font License 1.1 (docs/CREDITS.md).
const sans = Public_Sans({ subsets: ["latin"], variable: "--font-sans", display: "swap" });
const serif = Source_Serif_4({ subsets: ["latin"], variable: "--font-serif", display: "swap" });

export const metadata: Metadata = {
  title: { default: "Cluster Review Intelligence", template: "%s | Cluster Review Intelligence" },
  description:
    "For hotel and homestay owners in Uttarakhand: when your reviews get worse, is it your property or the whole market? Your cluster can tell.",
};

export const viewport: Viewport = { themeColor: "#4A6386" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${sans.variable} ${serif.variable}`}>
      <body>
        <a className="skip-link" href="#main">
          Skip to content
        </a>
        <DataProvider>
          <SyntheticBanner />
          <Header />
          <main id="main" className="main">
            {children}
          </main>
          <footer className="site-footer">
            <p>
              Cluster Review Intelligence is open source under the Apache License 2.0. Methods and
              limitations: <code>docs/methodology.md</code>. Accuracy on real reviews is{" "}
              <code>TBD</code> until a labelled set exists.
            </p>
          </footer>
        </DataProvider>
      </body>
    </html>
  );
}
