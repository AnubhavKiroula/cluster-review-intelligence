"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import ThemeToggle from "@/components/ThemeToggle";

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
          {/* Two series that run together and then part: the question the site answers.
              The solid line is the market, the dashed one the property that left it. */}
          <svg className="wordmark-mark" viewBox="0 0 32 20" aria-hidden focusable="false">
            <path d="M1 13 L10 8 L20 9.5 L31 5" />
            <path className="mark-split" d="M10 8 L20 13.5 L31 18" />
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
        <ThemeToggle />
      </div>
    </header>
  );
}
