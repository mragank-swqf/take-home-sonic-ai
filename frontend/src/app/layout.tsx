import type { Metadata } from "next";
import type { ReactNode } from "react";
import { AppNav } from "@/components/AppNav";
import "./globals.css";

export const metadata: Metadata = {
  title: "Sonic AI — AcmeCorp Accounts",
  description: "Collections and bank reconciliation take-home",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AppNav />
        <main>{children}</main>
      </body>
    </html>
  );
}
