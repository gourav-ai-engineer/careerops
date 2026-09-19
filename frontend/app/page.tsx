"use client";

import { useEffect, useMemo, useState } from "react";

type Summary = {
  jobs: { total: number; by_status: Record<string, number> };
  contacts: { total: number; verified: number; source_checked: number };
  fit: { average_score: number | null };
  runs: { total: number };
  recent_jobs: Array<{ id: number; company: string; title: string; location: string | null; status: string; application_url: string | null }>;
};

type ContactList = {
  items: Array<{ id: number; company_name: string; name: string | null; title: string | null; email: string | null; verification_status: string | null }>;
  total: number;
};

type Draft = {
  id: number;
  job_id: number;
  status: string;
  company_name: string;
  job_title: string;
  matched_keywords: string[];
  missing_keywords: string[];
};

const API = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API}${path}`, { ...init, cache: "no-store" });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

export default function Dashboard() {
  const [tab, setTab] = useState<"overview" | "jobs" | "contacts" | "resume">("overview");
  const [summary, setSummary] = useState<Summary | null>(null);
  const [jobs, setJobs] = useState<Summary["recent_jobs"]>([]);
  const [contacts, setContacts] = useState<ContactList | null>(null);
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [masterName, setMasterName] = useState("Master Resume");
  const [masterContent, setMasterContent] = useState("");
  const [resumeSaved, setResumeSaved] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const load = async () => {
    try {
      setError("");
      const s = await api<Summary>("/dashboard/summary");
      setSummary(s);
      const [j, c, d] = await Promise.all([
        api<{items: Summary["recent_jobs"]}>("/jobs?page=1&page_size=50"),
        api<ContactList>("/contacts/list?page=1&page_size=50"),
        api<Draft[]>("/resume/drafts?limit=50"),
        api<{id:number; name:string; version:number; content:string} | null>("/resume/master"),
      ]);
      setJobs(j.items);
      setContacts(c);
      setDrafts(d);
      if (master) {
        setMasterName(master.name);
        setMasterContent(master.content);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load dashboard");
    }
  };

  useEffect(() => { load(); }, []);

  const statuses = useMemo(() => Object.entries(summary?.jobs.by_status || {}), [summary]);

  const recalc = async () => {
    setBusy(true);
    try {
      await api("/jobs/fit-assessments/verified", { method: "POST" });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Fit recalculation failed");
    } finally {
      setBusy(false);
    }
  };

  const saveMaster = async () => {
    setBusy(true);
    setResumeSaved(false);
    try {
      await api("/resume/master", {
        method: "PUT",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify({name: masterName, content: masterContent}),
      });
      setResumeSaved(true);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Master resume save failed");
    } finally {
      setBusy(false);
    }
  };

  const setDraftStatus = async (id: number, status: string) => {
    try {
      await api(`/resume/drafts/${id}`, { method: "PATCH", headers: {"Content-Type":"application/json"}, body: JSON.stringify({status}) });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Draft update failed");
    }
  };

  return (
    <main className="shell">
      <header className="hero">
        <div>
          <p className="eyebrow">CAREER INTELLIGENCE</p>
          <h1>CareerOps</h1>
          <p className="sub">Jobs, verification, fit, professional contacts, resume workflow, and Smartsheet operations in one control surface.</p>
        </div>
        <button className="ghost" onClick={load}>Refresh</button>
      </header>

      <nav className="nav">
        {(["overview","jobs","contacts","resume"] as const).map(item => (
          <button key={item} className={tab === item ? "navItem active" : "navItem"} onClick={() => setTab(item)}>
            {item}
          </button>
        ))}
        <a className="navItem link" href={`${API}/docs`} target="_blank">api docs</a>
      </nav>

      {error && <div className="error">{error}</div>}

      {tab === "overview" && (
        <>
          <section className="grid stats">
            <Card title="Jobs" value={summary?.jobs.total ?? "—"} detail="All captured opportunities" />
            <Card title="Contacts" value={summary?.contacts.total ?? "—"} detail="Professional contact records" />
            <Card title="Verified contacts" value={summary?.contacts.verified ?? "—"} detail="Explicitly verified" />
            <Card title="Average fit" value={summary?.fit.average_score ?? "—"} detail="Persisted rule-based score" />
          </section>
          <section className="panel">
            <div className="panelHead">
              <div><h2>Pipeline status</h2><p>Current lifecycle counts from PostgreSQL.</p></div>
              <button className="primary" onClick={recalc} disabled={busy}>{busy ? "Recalculating…" : "Recalculate fit"}</button>
            </div>
            <div className="chips">{statuses.map(([status, count]) => <span className="chip" key={status}>{status}<b>{count}</b></span>)}</div>
          </section>
        </>
      )}

      {tab === "jobs" && (
        <section className="panel">
          <div className="panelHead"><div><h2>Jobs</h2><p>Latest stored opportunities.</p></div></div>
          <div className="table"><div className="row head"><span>Company</span><span>Role</span><span>Location</span><span>Status</span></div>
            {jobs.map(job => <div className="row" key={job.id}><span>{job.company}</span><span>{job.title}</span><span>{job.location || "—"}</span><span className="badge">{job.status}</span></div>)}
          </div>
        </section>
      )}

      {tab === "contacts" && (
        <section className="panel">
          <div className="panelHead"><div><h2>Contacts</h2><p>Professional contacts retained with source evidence.</p></div></div>
          <div className="table"><div className="row contactHead"><span>Company</span><span>Person</span><span>Email</span><span>Verification</span></div>
            {(contacts?.items || []).map(contact => <div className="row contactHead" key={contact.id}><span>{contact.company_name}</span><span>{contact.name || contact.title || "—"}</span><span>{contact.email || "—"}</span><span className="badge">{contact.verification_status || "unverified"}</span></div>)}
          </div>
        </section>
      )}

      {tab === "resume" && (
        <>
        <section className="panel">
          <div className="panelHead"><div><h2>Master resume</h2><p>Stored source document. Draft generation never overwrites it.</p></div><button className="primary" onClick={saveMaster} disabled={busy}>{busy ? "Saving…" : "Save master"}</button></div>
          <input className="resumeName" value={masterName} onChange={e => setMasterName(e.target.value)} placeholder="Resume name" />
          <textarea className="resumeEditor" value={masterContent} onChange={e => setMasterContent(e.target.value)} placeholder="Paste your master resume text here." />
          {resumeSaved && <p className="success">Master resume saved.</p>}
        </section>
        <section className="panel">
          <div className="panelHead"><div><h2>Resume drafts</h2><p>Drafts remain reviewable and never overwrite the master automatically.</p></div></div>
          <div className="drafts">
            {(drafts || []).map(draft => (
              <article className="draft" key={draft.id}>
                <div><strong>{draft.company_name} — {draft.job_title}</strong><span className="badge">{draft.status}</span></div>
                <p>Matched: {draft.matched_keywords.join(", ") || "none"}</p>
                <p>Missing: {draft.missing_keywords.join(", ") || "none"}</p>
                <div className="actions">
                  {draft.status === "draft" && <><button className="primary" onClick={() => setDraftStatus(draft.id, "approved")}>Approve</button><button className="ghost" onClick={() => setDraftStatus(draft.id, "rejected")}>Reject</button></>}
                </div>
              </article>
            ))}
          </div>
        </section>
        </>
      )}

      <footer><span>CareerOps v1.0</span><span>PostgreSQL → API → Dashboard / Smartsheet / Windmill</span></footer>
    </main>
  );
}

function Card({ title, value, detail }: { title: string; value: React.ReactNode; detail: string }) {
  return <div className="card"><p>{title}</p><strong>{value}</strong><span>{detail}</span></div>;
}
