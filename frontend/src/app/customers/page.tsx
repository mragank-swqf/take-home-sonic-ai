"use client";

import { FormEvent, useEffect, useState } from "react";
import { apiGet, apiSend } from "@/lib/api";

type Customer = {
  customer_id: string;
  name: string;
  contact_name: string;
  contact_email: string;
  phone: string;
  city: string;
  country: string;
  currency: string;
};

export default function CustomersPage() {
  const [items, setItems] = useState<Customer[]>([]);
  const [error, setError] = useState("");
  const [editing, setEditing] = useState<string | null>(null);
  const [email, setEmail] = useState("");
  const [msg, setMsg] = useState("");

  async function load() {
    const data = await apiGet<{ items: Customer[] }>("/api/customers");
    setItems(data.items);
  }

  useEffect(() => {
    load().catch((e: Error) => setError(e.message));
  }, []);

  async function save(e: FormEvent, customerId: string) {
    e.preventDefault();
    setMsg("");
    try {
      await apiSend(`/api/customers/${customerId}`, "PATCH", { contact_email: email });
      setEditing(null);
      setMsg(`Updated ${customerId}`);
      await load();
    } catch (err) {
      setMsg(err instanceof Error ? err.message : "Update failed");
    }
  }

  if (error) return <p className="error">{error}</p>;

  return (
    <>
      <h1>Customers</h1>
      {msg && <p>{msg}</p>}
      <div className="panel">
        <table className="data">
          <thead>
            <tr>
              <th>ID</th>
              <th>Name</th>
              <th>Contact</th>
              <th>Email</th>
              <th>Location</th>
              <th>CCY</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {items.map((c) => (
              <tr key={c.customer_id}>
                <td>{c.customer_id}</td>
                <td>{c.name}</td>
                <td>{c.contact_name}</td>
                <td>
                  {editing === c.customer_id ? (
                    <form onSubmit={(e) => save(e, c.customer_id)} className="row-actions">
                      <input
                        type="email"
                        value={email}
                        onChange={(ev) => setEmail(ev.target.value)}
                        required
                      />
                      <button className="primary" type="submit">
                        Save
                      </button>
                      <button type="button" onClick={() => setEditing(null)}>
                        Cancel
                      </button>
                    </form>
                  ) : (
                    c.contact_email
                  )}
                </td>
                <td>
                  {c.city}, {c.country}
                </td>
                <td>{c.currency}</td>
                <td>
                  {editing !== c.customer_id && (
                    <button
                      type="button"
                      onClick={() => {
                        setEditing(c.customer_id);
                        setEmail(c.contact_email);
                      }}
                    >
                      Edit email
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
