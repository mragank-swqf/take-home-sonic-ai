"use client";

import { FormEvent, useEffect, useState } from "react";
import { apiGet, apiSend, formatMinor } from "@/lib/api";

type Upload = { id: string; filename: string; row_count: number; uploaded_at: string };
type Candidate = { invoice_number: string; score: number };
type Hint = { invoice_number: string; why: string };
type Suggestion = {
  id: string;
  txn_date: string;
  narration: string;
  amount_minor: number;
  currency: string;
  direction: string;
  match_status: string;
  suggested_invoice_number: string | null;
  suggested_score: number | null;
  reason: string;
  candidates: Candidate[];
  ui_hints: Hint[];
  chosen_invoice_number: string | null;
  tds_required: boolean;
};

export default function ReconciliationPage() {
  const [uploads, setUploads] = useState<Upload[]>([]);
  const [activeUpload, setActiveUpload] = useState<string | null>(null);
  const [rows, setRows] = useState<Suggestion[]>([]);
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");

  async function refreshUploads() {
    const data = await apiGet<{ items: Upload[] }>("/api/reconciliation/uploads");
    setUploads(data.items);
    if (!activeUpload && data.items[0]) {
      setActiveUpload(data.items[0].id);
    }
  }

  async function loadSuggestions(uploadId: string) {
    const data = await apiGet<{ items: Suggestion[] }>(
      `/api/reconciliation/uploads/${uploadId}/suggestions`,
    );
    setRows(data.items);
  }

  useEffect(() => {
    refreshUploads().catch((e: Error) => setError(e.message));
  }, []);

  useEffect(() => {
    if (activeUpload) {
      loadSuggestions(activeUpload).catch((e: Error) => setError(e.message));
    }
  }, [activeUpload]);

  async function onUpload(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setMsg("");
    setError("");
    const form = e.currentTarget;
    const fileInput = form.elements.namedItem("file") as HTMLInputElement;
    const file = fileInput.files?.[0];
    if (!file) return;
    const body = new FormData();
    body.append("file", file);
    try {
      const res = await apiSend<{ upload_id: string }>("/api/reconciliation/uploads", "POST", body);
      setMsg(`Uploaded ${res.upload_id}`);
      await refreshUploads();
      setActiveUpload(res.upload_id);
      form.reset();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    }
  }

  async function approve(row: Suggestion, tds?: "close" | "leave_open") {
    setError("");
    try {
      await apiSend(`/api/reconciliation/rows/${row.id}/approve`, "POST", {
        invoice_number: row.chosen_invoice_number || row.suggested_invoice_number,
        tds_option: tds,
      });
      if (activeUpload) await loadSuggestions(activeUpload);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Approve failed");
    }
  }

  async function reject(rowId: string) {
    await apiSend(`/api/reconciliation/rows/${rowId}/reject`, "POST");
    if (activeUpload) await loadSuggestions(activeUpload);
  }

  async function choose(rowId: string, invoiceNumber: string) {
    await apiSend(`/api/reconciliation/rows/${rowId}/choose-invoice`, "POST", {
      invoice_number: invoiceNumber,
    });
    if (activeUpload) await loadSuggestions(activeUpload);
  }

  return (
    <>
      <h1>Bank reconciliation</h1>
      <div className="panel">
        <form onSubmit={onUpload} className="row-actions">
          <input name="file" type="file" accept=".csv,text/csv" required />
          <button className="primary" type="submit">
            Upload CSV
          </button>
        </form>
        {msg && <p>{msg}</p>}
        {error && <p className="error">{error}</p>}
        {uploads.length > 0 && (
          <p>
            Upload:{" "}
            <select
              value={activeUpload ?? ""}
              onChange={(e) => setActiveUpload(e.target.value)}
            >
              {uploads.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.filename} ({u.row_count}) — {u.uploaded_at}
                </option>
              ))}
            </select>
          </p>
        )}
      </div>

      <div className="panel">
        <table className="data">
          <thead>
            <tr>
              <th>Date</th>
              <th>Narration</th>
              <th>Amount</th>
              <th>Suggested</th>
              <th>Score</th>
              <th>Reason</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const suggested =
                row.chosen_invoice_number || row.suggested_invoice_number || "None";
              return (
                <tr key={row.id}>
                  <td>{row.txn_date}</td>
                  <td>{row.narration}</td>
                  <td>
                    {formatMinor(row.amount_minor, row.currency)}{" "}
                    <span className="muted">{row.direction}</span>
                  </td>
                  <td>
                    {suggested}
                    {row.ui_hints?.length > 0 && (
                      <div className="muted">
                        hint:{" "}
                        {row.ui_hints.map((h) => (
                          <button
                            key={h.invoice_number}
                            type="button"
                            onClick={() => choose(row.id, h.invoice_number)}
                            title={h.why}
                          >
                            {h.invoice_number}
                          </button>
                        ))}
                      </div>
                    )}
                  </td>
                  <td>{row.suggested_score ?? "—"}</td>
                  <td>
                    {row.reason}
                    {row.candidates?.length > 0 && row.match_status !== "approved" && (
                      <div className="row-actions" style={{ marginTop: "0.35rem" }}>
                        {row.candidates.map((c) => (
                          <button
                            key={c.invoice_number}
                            type="button"
                            onClick={() => choose(row.id, c.invoice_number)}
                          >
                            {c.invoice_number} ({c.score})
                          </button>
                        ))}
                      </div>
                    )}
                  </td>
                  <td className="row-actions">
                    {row.match_status === "ignored" && <span className="muted">ignored</span>}
                    {row.match_status === "approved" && <span className="badge paid">approved</span>}
                    {row.match_status === "rejected" && <span className="muted">rejected</span>}
                    {["pending", "suggested"].includes(row.match_status) && (
                      <>
                        {row.tds_required ? (
                          <>
                            <button type="button" onClick={() => approve(row, "close")}>
                              Close (TDS)
                            </button>
                            <button type="button" onClick={() => approve(row, "leave_open")}>
                              Leave open
                            </button>
                          </>
                        ) : (
                          <button
                            className="primary"
                            type="button"
                            disabled={suggested === "None"}
                            onClick={() => approve(row)}
                          >
                            Approve
                          </button>
                        )}
                        <button type="button" onClick={() => reject(row.id)}>
                          Reject
                        </button>
                      </>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </>
  );
}
