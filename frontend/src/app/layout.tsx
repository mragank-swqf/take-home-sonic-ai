import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "Sonic AI — AcmeCorp Accounts",
  description: "Collections and bank reconciliation take-home",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body style={{ margin: 0, fontFamily: "Georgia, 'Times New Roman', serif" }}>
        {children}
      </body>
    </html>
  );
}
