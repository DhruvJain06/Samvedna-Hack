"use client";

import { useEffect, useState } from "react";
import { Guard } from "@/components/Shell";
import { api } from "@/lib/api";
import { useLocale } from "@/i18n/LocaleProvider";
import { useSession } from "@/lib/session";

type TrustRow = { role: string; action: string; outcome: string };
type TrustLatest = { date: string | null; results: TrustRow[]; overall: string | null };

function rowClass(outcome: string): string {
  if (outcome === "PASS") return "trust-pass";
  if (outcome === "FAIL") return "trust-fail";
  return "trust-hold";
}

export default function TrustPage() {
  return (
    <Guard need="auditor">
      <TrustConsole />
    </Guard>
  );
}

function TrustConsole() {
  const { session } = useSession();
  const { t } = useLocale();
  const [data, setData] = useState<TrustLatest | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!session) return;
    api.trustTestsLatest(session).then(setData).catch((e) => setError(String(e.message ?? e)));
  }, [session]);

  if (error) return <div className="banner stop" style={{ marginTop: 30 }}>{error}</div>;
  if (!data) return <p className="faint" style={{ paddingTop: 34 }}>Loading trust tests…</p>;

  if (!data.date && data.results.length === 0) {
    return (
      <>
        <div className="page-head">
          <p className="eyebrow">Governance · nightly RBAC</p>
          <h1>{t("trust.title")}</h1>
        </div>
        <p className="faint" style={{ marginTop: 16 }}>{t("trust.empty")}</p>
      </>
    );
  }

  return (
    <>
      <div className="page-head">
        <p className="eyebrow">Governance · nightly RBAC</p>
        <h1>{t("trust.title")}</h1>
        <p className="lede">Last run: {data.date ?? "unknown"}</p>
      </div>
      {data.overall === "FAIL" && (
        <div className="banner stop" style={{ marginTop: 12 }}>{t("trust.failBanner")}</div>
      )}
      <div className="card" style={{ marginTop: 16, overflowX: "auto" }}>
        <table className="plain">
          <thead>
            <tr>
              <th>Role</th>
              <th>Action</th>
              <th>Outcome</th>
            </tr>
          </thead>
          <tbody>
            {data.results.map((row) => (
              <tr key={`${row.role}-${row.action}`} className={rowClass(row.outcome)}>
                <td>{row.role}</td>
                <td>{row.action}</td>
                <td>
                  {row.outcome === "FAIL" ? "⚠ " : ""}
                  {row.outcome}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
