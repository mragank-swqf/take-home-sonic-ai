"use client";

import { useEffect, useState } from "react";
import { apiGet } from "@/lib/api";

type Org = {
  name: string;
  address: string;
  phone: string;
  accounts_contact_name: string;
  accounts_email: string;
  default_currency: string;
  accepted_currencies: string[];
  payment_methods: string[];
  bank_details: Record<string, string>;
  policies: Record<string, string>;
};

export default function OrganizationPage() {
  const [org, setOrg] = useState<Org | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    apiGet<Org>("/api/organization")
      .then(setOrg)
      .catch((e: Error) => setError(e.message));
  }, []);

  if (error) return <p className="error">{error}</p>;
  if (!org) return <p className="muted">Loading…</p>;

  return (
    <>
      <h1>{org.name}</h1>
      <div className="panel">
        <p>{org.address}</p>
        <p>
          Accounts: {org.accounts_contact_name} · {org.accounts_email}
        </p>
        <p>Phone: {org.phone}</p>
        <p>
          Currencies: {org.accepted_currencies.join(", ")} (default {org.default_currency})
        </p>
        <p>Payment methods: {org.payment_methods.join(", ")}</p>
        <h2>Bank details</h2>
        <ul>
          {Object.entries(org.bank_details).map(([k, v]) => (
            <li key={k}>
              <strong>{k}</strong>: {v}
            </li>
          ))}
        </ul>
        <h2>Policies</h2>
        <ul>
          {Object.entries(org.policies).map(([k, v]) => (
            <li key={k}>
              <strong>{k}</strong>: {v}
            </li>
          ))}
        </ul>
      </div>
    </>
  );
}
