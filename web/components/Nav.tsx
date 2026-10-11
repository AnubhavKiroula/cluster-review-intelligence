"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/", label: "Home", icon: "🏔️" },
  { href: "/property", label: "Property", icon: "🏨" },
  { href: "/cluster", label: "Cluster", icon: "🗺️" },
  { href: "/market", label: "Market", icon: "⚖️" },
  { href: "/destination", label: "Destination", icon: "🧭" },
  { href: "/explorer", label: "Explorer", icon: "🔍" },
];

export default function Nav() {
  const pathname = usePathname();
  return (
    <nav className="nav">
      <div className="nav-brand">
        <span aria-hidden>🏔️</span> Cluster Review Intelligence
      </div>
      <ul className="nav-links">
        {LINKS.map((l) => {
          const active = l.href === "/" ? pathname === "/" : pathname.startsWith(l.href);
          return (
            <li key={l.href}>
              <Link href={l.href} className={active ? "nav-link active" : "nav-link"}>
                <span aria-hidden>{l.icon}</span> {l.label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
