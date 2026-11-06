"use client";

import { useEffect, useState } from "react";

type HealthState =
  | { kind: "loading" }
  | { kind: "ok"; status: string }
  | { kind: "error"; message: string };

export default function HomePage() {
  const [health, setHealth] = useState<HealthState>({ kind: "loading" });
  const apiBase = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(`${apiBase}/health`, { cache: "no-store" });
        if (!res.ok) {
          if (!cancelled) setHealth({ kind: "error", message: `HTTP ${res.status}` });
          return;
        }
        const body = (await res.json()) as { status: string };
        if (!cancelled) setHealth({ kind: "ok", status: body.status });
      } catch (err) {
        if (!cancelled) {
          setHealth({
            kind: "error",
            message: err instanceof Error ? err.message : "request failed",
          });
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [apiBase]);

  return (
    <main
      style={{
        minHeight: "100vh",
        padding: "3rem 1.5rem",
        background: "linear-gradient(165deg, #eef3f0 0%, #d9e4dd 55%, #c9d6cf 100%)",
        color: "#152019",
      }}
    >
      <p style={{ letterSpacing: "0.08em", textTransform: "uppercase", fontSize: "0.8rem" }}>
        Sonic AI · take-home
      </p>
      <h1 style={{ fontSize: "2.4rem", margin: "0.4rem 0 0.75rem" }}>AcmeCorp Accounts</h1>
      <p style={{ maxWidth: "36rem", lineHeight: 1.5 }}>
        Docker scaffold is up. Specs live in <code>specs/</code>; application features come next.
      </p>
      <p style={{ marginTop: "1.5rem" }}>
        API health ({apiBase}):{" "}
        <strong
          style={{
            color: health.kind === "ok" ? "#1b6b45" : health.kind === "error" ? "#8a1f1f" : "#44554a",
          }}
        >
          {health.kind === "loading" && "checking…"}
          {health.kind === "ok" && health.status}
          {health.kind === "error" && `error — ${health.message}`}
        </strong>
      </p>
    </main>
  );
}
