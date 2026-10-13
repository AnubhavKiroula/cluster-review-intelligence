"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/property", label: "Your property" },
  { href: "/market", label: "The market" },
  { href: "/fix-check", label: "Did my fix work?" },
  { href: "/explorer", label: "Review explorer" },
];

// Exact match on path segments: a prefix test lit /explorer for /explore too.
function isActive(href: string, pathname: string): boolean {
  const path = pathname.replace(/\/+$/, "") || "/";
  return href === "/" ? path === "/" : path === href || path.startsWith(`${href}/`);
}

export default function Header() {
  const pathname = usePathname();
  return (
    <header className="site-header">
      <div className="site-header-inner">
        <Link href="/" className="wordmark" aria-current={isActive("/", pathname) ? "page" : undefined}>
          <svg className="wordmark-mark" viewBox="0 0 32 20" aria-hidden>
            <path d="M1 19 L10 6 L15 12 L21 3 L31 19 Z" />
          </svg>
          Cluster Review Intelligence
        </Link>
        <nav aria-label="Main">
          <ul className="nav-links">
            {LINKS.map((l) => {
              const active = isActive(l.href, pathname);
              return (
                <li key={l.href}>
                  <Link
                    href={l.href}
                    className={active ? "nav-link active" : "nav-link"}
                    aria-current={active ? "page" : undefined}
                  >
                    {l.label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>
      </div>
    </header>
  );
}
