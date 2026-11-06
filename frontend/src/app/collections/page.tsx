"use client";

import { useEffect, useState } from "react";
import { apiGet, apiSend } from "@/lib/api";

type Conversation = {
  id: string;
  customer_id: string | null;
  subject: string;
  status: string;
  needs_attention_reason?: string;
  last_message_at?: string;
};

type NeedsItem = {
  conversation_id: string;
  customer_id: string | null;
  subject: string;
  reason: string;
  pending_draft: string | null;
  pending_intent: string | null;
  latest_inbound_snippet: string;
};

type Message = {
  id: string;
  direction: string;
  from_email: string;
  body_text: string;
  sent_at?: string;
  kind?: string;
};

export default function CollectionsPage() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [needs, setNeeds] = useState<NeedsItem[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [draft, setDraft] = useState("");
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");

  async function refresh() {
    const [c, n] = await Promise.all([
      apiGet<{ items: Conversation[] }>("/api/collections/conversations"),
      apiGet<{ items: NeedsItem[] }>("/api/collections/needs-attention"),
    ]);
    setConversations(c.items);
    setNeeds(n.items);
  }

  useEffect(() => {
    refresh().catch((e: Error) => setError(e.message));
  }, []);

  useEffect(() => {
    if (!activeId) return;
    apiGet<{ messages: Message[]; pending_draft?: string }>(
      `/api/collections/conversations/${activeId}`,
    )
      .then((d) => {
        setMessages(d.messages);
        if (d.pending_draft) setDraft(d.pending_draft);
      })
      .catch((e: Error) => setError(e.message));
  }, [activeId]);

  async function sendReminders() {
    setMsg("");
    try {
      const res = await apiSend<{ sent: unknown[]; skipped: { customer_id: string; reason: string }[] }>(
        "/api/collections/reminders/send",
        "POST",
        {},
      );
      setMsg(`Sent ${res.sent.length}; skipped ${res.skipped.length}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed");
    }
  }

  async function checkInbox() {
    setMsg("");
    try {
      const res = await apiSend<{ processed: number; needs_attention: number; sent_replies: number }>(
        "/api/collections/inbox/check",
        "POST",
      );
      setMsg(
        `Processed ${res.processed}; auto-replies ${res.sent_replies}; needs attention ${res.needs_attention}`,
      );
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "IMAP failed");
    }
  }

  async function forceReminder(customerId: string) {
    await apiSend(`/api/collections/reminders/send/${customerId}`, "POST", { force: true });
    setMsg(`Forced reminder for ${customerId}`);
  }

  async function saveDraft(id: string) {
    await apiSend(`/api/collections/needs-attention/${id}`, "PATCH", { draft });
    setMsg("Draft saved");
  }

  async function sendDraft(id: string) {
    await apiSend(`/api/collections/needs-attention/${id}/send`, "POST", { draft });
    setMsg("Sent");
    setDraft("");
    await refresh();
  }

  return (
    <>
      <h1>Collections</h1>
      <div className="panel row-actions">
        <button className="primary" type="button" onClick={sendReminders}>
          Send overdue reminders
        </button>
        <button type="button" onClick={checkInbox}>
          Check inbox now
        </button>
      </div>
      {msg && <p>{msg}</p>}
      {error && <p className="error">{error}</p>}

      <h2>Needs attention</h2>
      <div className="panel">
        {needs.length === 0 && <p className="muted">None</p>}
        {needs.map((n) => (
          <div key={n.conversation_id} style={{ marginBottom: "1rem" }}>
            <p>
              <strong>{n.subject}</strong> · {n.customer_id || "unknown"} · {n.reason}
            </p>
            <p className="muted">{n.latest_inbound_snippet}</p>
            <textarea
              rows={4}
              value={activeId === n.conversation_id ? draft : n.pending_draft || ""}
              onFocus={() => {
                setActiveId(n.conversation_id);
                setDraft(n.pending_draft || "");
              }}
              onChange={(e) => setDraft(e.target.value)}
            />
            <div className="row-actions" style={{ marginTop: "0.4rem" }}>
              <button type="button" onClick={() => saveDraft(n.conversation_id)}>
                Save draft
              </button>
              <button className="primary" type="button" onClick={() => sendDraft(n.conversation_id)}>
                Send
              </button>
              {n.customer_id && (
                <button type="button" onClick={() => forceReminder(n.customer_id!)}>
                  Send reminder now
                </button>
              )}
            </div>
          </div>
        ))}
      </div>

      <h2>Conversations</h2>
      <div className="panel">
        <table className="data">
          <thead>
            <tr>
              <th>Customer</th>
              <th>Subject</th>
              <th>Status</th>
              <th>Updated</th>
            </tr>
          </thead>
          <tbody>
            {conversations.map((c) => (
              <tr key={c.id} onClick={() => setActiveId(c.id)} style={{ cursor: "pointer" }}>
                <td>{c.customer_id || "—"}</td>
                <td>{c.subject}</td>
                <td>{c.status}</td>
                <td>{c.last_message_at}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {activeId && (
          <div style={{ marginTop: "1rem" }}>
            <h3>Thread</h3>
            {messages.map((m) => (
              <div key={m.id} style={{ marginBottom: "0.75rem" }}>
                <p className="muted">
                  {m.direction} · {m.from_email} · {m.sent_at} · {m.kind}
                </p>
                <pre
                  style={{
                    whiteSpace: "pre-wrap",
                    fontFamily: "inherit",
                    margin: 0,
                    background: "#fff",
                    padding: "0.5rem",
                    borderRadius: 8,
                  }}
                >
                  {m.body_text}
                </pre>
              </div>
            ))}
          </div>
        )}
      </div>
    </>
  );
}
