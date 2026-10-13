"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useData } from "@/lib/data";

const LINKS = [
  { href: "/", label: "Home", icon: "🏔️" },
  { href: "/property", label: "Property", icon: "🏨" },
  { href: "/cluster", label: "Cluster", icon: "🗺️" },
  { href: "/market", label: "Market", icon: "⚖️" },
  { href: "/destination", label: "Destination", icon: "🧭" },
  { href: "/explorer", label: "Explorer", icon: "🔍" },
  { href: "/fix-check", label: "Did my fix work?", icon: "🔧" },
];

// Travel intelligence pages: these call the Python API (cri.server), see lib/api.ts.
const TRAVEL_LINKS = [
  { href: "/explore", label: "When & where to go", icon: "🧭" },
  { href: "/plan", label: "Plan a trip", icon: "🗺️" },
  { href: "/provider", label: "Provider insights", icon: "🛎️" },
  { href: "/region", label: "Regional pressure", icon: "🏔️" },
];

function NavList({ links, pathname }: { links: typeof LINKS; pathname: string }) {
  return (
    <ul className="nav-links">
      {links.map((l) => {
        const active = l.href === "/" ? pathname === "/" : pathname.startsWith(l.href);
        return (
          <li key={l.href}>
            <Link href={l.href} className={active ? "nav-link active" : "nav-link"}>
              <span className="nav-icon" aria-hidden>
                {l.icon}
              </span>
              {l.label}
            </Link>
          </li>
        );
      })}
    </ul>
  );
}

export default function Nav() {
  const pathname = usePathname();
  const { data } = useData();
  return (
    <nav className="nav">
      <div className="nav-brand">
        <div className="brand-mark" aria-hidden>
          ◒
        </div>
        <div>
          <div className="brand-title">Cluster Review</div>
          <div className="brand-subtitle">Intelligence workspace</div>
        </div>
      </div>
      <div className="nav-section-label">Workspace</div>
      <NavList links={LINKS} pathname={pathname} />
      <div className="nav-section-label">Travel intelligence</div>
      <NavList links={TRAVEL_LINKS} pathname={pathname} />
      <div className="nav-footer">
        <div className="workspace-card">
          <span className="status-dot" aria-hidden />
          <div>
            <strong>{data?.meta.is_synthetic ? "Synthetic workspace" : "Connected workspace"}</strong>
            <small>{data ? `${data.meta.properties.length} properties · ${data.meta.n_reviews.toLocaleString()} reviews` : "Loading cluster snapshot…"}</small>
          </div>
        </div>
      </div>
    </nav>
  );
}
