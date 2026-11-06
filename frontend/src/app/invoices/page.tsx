"use client";

import { useEffect, useState } from "react";
import { apiGet, formatMinor } from "@/lib/api";

type Invoice = {
  invoice_number: string;
  customer_id: string;
  customer_name: string;
  due_date: string;
  currency: string;
  status: string;
  total_minor: number;
  balance_due_minor: number;
  unpaid_amount_minor: number;
  is_overdue: boolean;
};

export default function InvoicesPage() {
  const [items, setItems] = useState<Invoice[]>([]);
  const [asOf, setAsOf] = useState("");
  const [overdueOnly, setOverdueOnly] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const q = overdueOnly ? "?overdue=true" : "";
    apiGet<{ items: Invoice[]; as_of: string }>(`/api/invoices${q}`)
      .then((d) => {
        setItems(d.items);
        setAsOf(d.as_of);
      })
      .catch((e: Error) => setError(e.message));
  }, [overdueOnly]);

  if (error) return <p className="error">{error}</p>;

  return (
    <>
      <h1>Invoices</h1>
      <p className="muted">As of {asOf || "…"} (overdue is computed, never stored).</p>
      <label>
        <input
          type="checkbox"
          checked={overdueOnly}
          onChange={(e) => setOverdueOnly(e.target.checked)}
        />{" "}
        Overdue only
      </label>
      <div className="panel">
        <table className="data">
          <thead>
            <tr>
              <th>Invoice</th>
              <th>Customer</th>
              <th>Due</th>
              <th>Status</th>
              <th>Total</th>
              <th>Unpaid</th>
            </tr>
          </thead>
          <tbody>
            {items.map((inv) => (
              <tr key={inv.invoice_number}>
                <td>{inv.invoice_number}</td>
                <td>
                  {inv.customer_name} ({inv.customer_id})
                </td>
                <td>{inv.due_date}</td>
                <td>
                  <span className={`badge ${inv.is_overdue ? "overdue" : inv.status}`}>
                    {inv.is_overdue ? "overdue" : inv.status}
                  </span>
                </td>
                <td>{formatMinor(inv.total_minor, inv.currency)}</td>
                <td>{formatMinor(inv.unpaid_amount_minor, inv.currency)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
