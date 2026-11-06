"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/", label: "Home" },
  { href: "/organization", label: "Organization" },
  { href: "/customers", label: "Customers" },
  { href: "/invoices", label: "Invoices" },
  { href: "/collections", label: "Collections" },
  { href: "/reconciliation", label: "Reconciliation" },
];

export function AppNav() {
  const pathname = usePathname();
  return (
    <nav className="app-nav">
      <Link href="/" className="brand">
        Sonic · AcmeCorp
      </Link>
      {LINKS.map((link) => (
        <Link
          key={link.href}
          href={link.href}
          style={{ fontWeight: pathname === link.href ? 700 : 400 }}
        >
          {link.label}
        </Link>
      ))}
    </nav>
  );
}
