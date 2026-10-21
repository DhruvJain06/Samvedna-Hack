"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import type { Caseload, RunSummary } from "@/lib/types";
import { DEFAULT_SESSION, api } from "@/lib/api";

const SCALE = [
  {
    figure: "654",
    label: "CAPF suicides",
    note: "2018–2022",
    tone: "stop",
  },
  {
    figure: "~1 in 3 days",
    label: "average interval",
    note: "between CAPF suicides",
    tone: "accent",
  },
  {
    figure: "50,155",
    label: "resigned or took VRS",
    note: "in five years",
    tone: "",
  },
  {
    figure: "~10 lakh+",
    label: "personnel addressable",
    note: "CAPF and Armed Forces",
    tone: "mid",
  },
];

const GATES = [
  {
    name: "Evidence",
    threshold: "0.65",
    asks: "Is there enough corroborated signal to be talking about a person at all?",
    guard: "One domain alone can never clear it. The arithmetic will not allow it.",
  },
  {
    name: "Consistency",
    threshold: "0.70",
    asks: "Do the signals agree, or is one anomaly shouting?",
    guard: "A unit deployment, sanctioned leave or a records gap pushes this down.",
  },
  {
    name: "Persistence",
    threshold: "0.60",
    asks: "Sustained, or a bad week?",
    guard: "Weighted to 30 days: long enough to exclude a rough patch, short enough to act.",
  },
  {
    name: "Actionability",
    threshold: "0.50",
    asks: "Is there a welfare action that fits and is not already being taken?",
    guard: "Three hard vetoes. No consent to contact forces this to exactly zero.",
  },
];

const AUDIENCES = [
  {
    who: "Personnel",
    sees: "their own data only",
    gets: "Early support before a crisis, and dignity preserved — no name leaves the system on weak evidence. They can see the same reasons the officer saw, and disagree with them.",
  },
  {
    who: "Welfare officers",
    sees: "escalated cases in their unit",
    gets: "A ranked, explained caseload instead of manual observation, with a recommended intervention attached and the argument against the flag shown first.",
  },
  {
    who: "Commanders",
    sees: "unit aggregates only",
    gets: "Fatigue and workload heat maps for rebalancing rosters and leave — never individual psychological data, and no drill-down exists to build one.",
  },
  {
    who: "The organisation",
    sees: "governance and audit",
    gets: "Evidence-based welfare planning, resource allocation and posting-cycle design, with every access and verdict reviewable.",
  },
];

const PHASES = [
  [
    "Phase 1",
    "Pilot — one battalion",
    "Retrospective data only. Shadow mode: the gates run and every verdict is recorded, but no alert is issued to anybody. Enforced by the dispatcher, not by operators remembering.",
  ],
  [
    "Phase 2",
    "Sector rollout",
    "Live alerts to welfare officers. Thresholds calibrated against real officer outcomes rather than a training metric.",
  ],
  [
    "Phase 3",
    "Force-wide",
    "Federated training across units. Raw records never leave the unit; only clipped, noised parameters do.",
  ],
];

const DOMAINS = [
  { name: "Self-assessment", tier: "T1", note: "Validated instrument, volunteered by the person" },
  { name: "Leave pattern", tier: "T2", note: "Applications denied, leave cancelled" },
  { name: "Duty roster", tier: "T2", note: "Consecutive days without a clear break" },
  { name: "Deployment", tier: "T2", note: "Time deployed away from station" },
  { name: "Workload", tier: "T2", note: "Duty hours above unit establishment" },
  { name: "Transfer", tier: "T3", note: "Postings in the trailing year" },
  { name: "Training", tier: "T3", note: "Course and training days assigned" },
  { name: "Biometric", tier: "T3", note: "Opt-in resting heart-rate trend" },
];

const PIPELINE = [
  ["01", "Ingest", "Seven service-record connectors pull leave, roster, deployment, workload, transfer, training, self-report."],
  ["02", "Protect", "Service number becomes a pseudonym, then the consent filter runs. No identifier goes past this line."],
  ["03", "Features", "Personal and unit baselines over 7, 30, 90 and 180 days."],
  ["04", "Deviate", "Who has moved from their own baseline — not from a fixed threshold everyone is measured against."],
  ["05", "Score", "The risk model runs. If it is missing the night continues; the gates do not need it."],
  ["06", "Review", "Three reviewers argue in parallel: the case for, the case against, and what was tried before."],
];

export default function Overview() {
  const [run, setRun] = useState<RunSummary | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    // Attempt caseload first, gracefully fallback to the public /api/run
    api
      .run()
      .then(setRun)
      .catch((e) => setError(String(e.message ?? e)));
  }, []);

  const screened = run ? String(run.screened) : null;
  const deviating = run ? String(run.deviating) : null;
  const named = run?.escalated ?? 0;
  const watched = run ? Math.max(0, run.deviating - run.escalated) : 0;
  const headline = run
    ? `${run.screened} screened • ${run.deviating} deviating • ${run.escalated} escalated to an officer`
    : "";

  return (
    <>
      <div className="hero">
        <div className="hero-inner">
          <p className="eyebrow">
            Smart India Hackathon 2026 • PS 26186 • Team CodeZila
          </p>
          <h1>
            Evidence-Gated Stress &amp;
            <br />
            Welfare Intelligence
          </h1>
          <p className="hero-quote">
            &ldquo;It flags a soldier only when the evidence earns it.&rdquo;
          </p>
          <p className="lede">
            SAMVEDNA finds early indicators of stress and burnout among CAPF and
            Armed Forces personnel, from records the force already holds plus
            voluntary self-assessment. Then it does the unusual part: it refuses
            to hand over a name unless four separate arithmetic tests all clear.
          </p>
          <div className="row" style={{ marginTop: 10 }}>
            <Link href="/demo" className="hero-cta">
              Take the guided walkthrough →
            </Link>
            <Link href="/signin" className="hero-cta ghost">
              Sign in as a role
            </Link>
          </div>
        </div>
      </div>

      <div className="shell">
        {error && (
          <div className="banner warn">
            <strong>Backend not reachable.</strong>
            <span>
              Start it with <code>uv run samvedna serve</code>. Every figure on
              this page comes from a live run.
            </span>
          </div>
        )}

        {run && (
          <div className="stack">
            <div className="headline">{headline}</div>
            <div className="grid grid-4">
              <div className="stat mid">
                <span className="n num">{screened ?? "—"}</span>
                <span className="k">screened overnight</span>
                <span className="sub">every consenting person in the force</span>
              </div>
              <div className="stat">
                <span className="n num">{deviating ?? "—"}</span>
                <span className="k">deviating</span>
                <span className="sub">moved from their own baseline</span>
              </div>
              <div className="stat pass">
                <span className="n num">{watched}</span>
                <span className="k">watched, not named</span>
                <span className="sub">the evidence did not hold up</span>
              </div>
              <div className="stat accent">
                <span className="n num">{named}</span>
                <span className="k">named to an officer</span>
                <span className="sub">cleared all four gates</span>
              </div>
            </div>
          </div>
        )}

        <section className="section">
          <p className="eyebrow">Why this exists</p>
          <h2>The scale of the problem</h2>
          <div className="grid grid-4" style={{ marginTop: 6 }}>
            {SCALE.map((s) => (
              <div key={s.label} className={`stat ${s.tone}`}>
                <span className="n num">{s.figure}</span>
                <span className="k">{s.label}</span>
                <span className="sub">{s.note}</span>
              </div>
            ))}
          </div>
        </section>

        <section className="section">
          <p className="eyebrow">The solution</p>
          <h2>Four gates. No single point of accusation.</h2>
          <div className="grid grid-2" style={{ marginTop: 6 }}>
            {GATES.map((g) => (
              <div key={g.name} className="card lifted">
                <div className="row">
                  <h3>{g.name} Gate</h3>
                  <span className="spacer" />
                  <span className="pill mono">{g.threshold}</span>
                </div>
                <p className="muted" style={{ marginTop: 10 }}>{g.asks}</p>
                <p className="faint" style={{ marginTop: 8 }}>{g.guard}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="section">
          <p className="eyebrow">Who sees what</p>
          <h2>Strict Role-Based Access</h2>
          <div className="grid grid-2" style={{ marginTop: 6 }}>
            {AUDIENCES.map((a) => (
              <div key={a.who} className="card">
                <h3>{a.who}</h3>
                <p className="faint" style={{ marginTop: 4 }}>
                  <strong>Scope:</strong> {a.sees}
                </p>
                <p className="muted" style={{ marginTop: 8 }}>{a.gets}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="section">
          <p className="eyebrow">Phased Deployment</p>
          <h2>Deployment Roadmap</h2>
          <div className="grid grid-3" style={{ marginTop: 6 }}>
            {PHASES.map(([phase, title, desc]) => (
              <div key={phase} className="card">
                <span className="pill info">{phase}</span>
                <h3 style={{ marginTop: 10 }}>{title}</h3>
                <p className="muted" style={{ marginTop: 8 }}>{desc}</p>
              </div>
            ))}
          </div>
        </section>
      </div>
    </>
  );
}
