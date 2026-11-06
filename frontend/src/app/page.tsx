"use client";

import { useEffect, useState } from "react";
import { apiGet, apiSend, apiUrl } from "@/lib/api";

export default function HomePage() {
  const [health, setHealth] = useState("checking…");
  const [resetMsg, setResetMsg] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    apiGet<{ status: string }>("/health")
      .then((d) => setHealth(d.status))
      .catch((e: Error) => setHealth(`error — ${e.message}`));
  }, []);

  async function resetDemo() {
    setBusy(true);
    setResetMsg("");
    try {
      const res = await apiSend<{ ok: boolean; seeded: { customers: number; invoices: number } }>(
        "/api/demo/reset",
        "POST",
      );
      setResetMsg(`Reset OK — ${res.seeded.customers} customers, ${res.seeded.invoices} invoices.`);
    } catch (e) {
      setResetMsg(e instanceof Error ? e.message : "Reset failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <h1>AcmeCorp Accounts</h1>
      <p className="muted">
        Collections agent + bank reconciliation. API: <code>{apiUrl("")}</code>
      </p>
      <div className="panel">
        <p>
          Health: <strong>{health}</strong>
        </p>
        <p className="muted">
          Known limitation: no authentication. Ports bind to 127.0.0.1 only.
        </p>
        <button className="primary" type="button" disabled={busy} onClick={resetDemo}>
          Reset demo data
        </button>
        {resetMsg && <p>{resetMsg}</p>}
      </div>
    </>
  );
}
