import type { Metadata, Viewport } from "next";
import { IBM_Plex_Sans, IBM_Plex_Sans_Devanagari, Literata } from "next/font/google";
import "./globals.css";
import Header from "@/components/Nav";
import { DataProvider } from "@/lib/data";
import { THEME_BOOT } from "@/lib/theme-boot";

// Self-hosted at build time by next/font: the browser makes no requests to Google.
// All three are SIL Open Font License 1.1 (docs/CREDITS.md).
//
// Literata reads as a report rather than a product page, and holds up at both 60px
// and 15px. Plex Sans carries the interface and the numbers (true tabular figures).
// Plex Sans Devanagari is not decoration: 781 of the 5,124 sample reviews contain
// Devanagari, and it sits after Plex Sans in the stack, so Hindi clauses in the
// explorer resolve to a face from the same family instead of a system fallback.
const serif = Literata({ subsets: ["latin"], variable: "--font-serif", display: "swap" });
const sans = IBM_Plex_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-sans",
  display: "swap",
});
const devanagari = IBM_Plex_Sans_Devanagari({
  subsets: ["devanagari"],
  weight: ["400", "500"],
  variable: "--font-devanagari",
  display: "swap",
});

export const metadata: Metadata = {
  title: { default: "Cluster Review Intelligence", template: "%s | Cluster Review Intelligence" },
  description:
    "For hotel and homestay owners in Uttarakhand: when your reviews get worse, is it your property or the whole market? Your cluster can tell.",
};

// Matches the header at the top of every page, in each colour scheme. An explicit
// choice in the header appends its own theme-color meta (applyMode in lib/theme.ts).
export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#FFFFFF" },
    { media: "(prefers-color-scheme: dark)", color: "#1B2420" },
  ],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${sans.variable} ${serif.variable} ${devanagari.variable}`}>
      <body>
        {/* First thing in the body, and synchronous, so the stored colour scheme is
            on <html> before anything paints. It has to be a plain tag here: inside
            <head> the App Router drops it from the exported HTML, and next/script
            with beforeInteractive only reaches the flight payload under
            `output: export`, which runs after hydration — too late to prevent the
            flash it exists to prevent. */}
        <script dangerouslySetInnerHTML={{ __html: THEME_BOOT }} />
        <a className="skip-link" href="#main">
          Skip to content
        </a>
        <DataProvider>
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
