"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useData } from "@/lib/data";

const LINKS = [
  { href: "/", label: "Home", icon: "🏔️" },
  { href: "/property", label: "Property", icon: "🏨" },
  { href: "/market", label: "Market", icon: "⚖️" },
  { href: "/fix-check", label: "Did my fix work?", icon: "🔧" },
  { href: "/explorer", label: "Explorer", icon: "🔍" },
];

// Exact match on path segments: a prefix test lit /explorer for /explore too.
function isActive(href: string, pathname: string): boolean {
  const path = pathname.replace(/\/+$/, "") || "/";
  return href === "/" ? path === "/" : path === href || path.startsWith(`${href}/`);
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
      <ul className="nav-links">
        {LINKS.map((l) => (
          <li key={l.href}>
            <Link
              href={l.href}
              className={isActive(l.href, pathname) ? "nav-link active" : "nav-link"}
            >
              <span className="nav-icon" aria-hidden>
                {l.icon}
              </span>
              {l.label}
            </Link>
          </li>
        ))}
      </ul>
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
