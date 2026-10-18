"use client";

import { useEffect, useMemo, useState } from "react";
import { Guard } from "@/components/Shell";
import { api } from "@/lib/api";
import { useLocale } from "@/i18n/LocaleProvider";
import { useSession } from "@/lib/session";

type Baseline = {
  capf_suicide_per_year?: number;
  capf_suicide_5yr?: number;
  burnout_specificity?: number;
  target_auroc?: number;
  source?: string;
  source_date?: string;
  notes?: string;
  last_checked?: string | null;
};

const FIELDS: { key: keyof Baseline; label: string }[] = [
  { key: "capf_suicide_per_year", label: "CAPF suicides / year" },
  { key: "capf_suicide_5yr", label: "CAPF suicides (5yr)" },
  { key: "burnout_specificity", label: "Burnout specificity" },
  { key: "target_auroc", label: "Target AUROC" },
];

function stale(lastChecked: string | null | undefined): boolean {
  if (!lastChecked) return true;
  const then = Date.parse(lastChecked);
  if (Number.isNaN(then)) return true;
  return Date.now() - then > 30 * 24 * 60 * 60 * 1000;
}

export default function EvidencePage() {
  return (
    <Guard need={["auditor", "mental_health_authority"]}>
      <EvidenceConsole />
    </Guard>
  );
}

function EvidenceConsole() {
  const { session } = useSession();
  const { t } = useLocale();
  const [data, setData] = useState<Baseline | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!session) return;
    api.evidenceBaseline(session).then(setData).catch((e) => setError(String(e.message ?? e)));
  }, [session]);

  const warn = useMemo(() => data && stale(data.last_checked ?? null), [data]);

  if (error) return <div className="banner stop" style={{ marginTop: 30 }}>{error}</div>;
  if (!data) return <p className="faint" style={{ paddingTop: 34 }}>Loading evidence baselines…</p>;

  return (
    <>
      <div className="page-head">
        <p className="eyebrow">Governance · read-only</p>
        <h1>{t("evidence.title")}</h1>
      </div>
      {warn && <div className="banner hold" style={{ marginTop: 12 }}>{t("evidence.stale")}</div>}
      <div className="card" style={{ marginTop: 16, overflowX: "auto" }}>
        <table className="plain">
          <thead>
            <tr>
              <th>Field</th>
              <th>Baseline value</th>
              <th>Source</th>
              <th>Last checked</th>
            </tr>
          </thead>
          <tbody>
            {FIELDS.map((field) => (
              <tr key={field.key}>
                <td>{field.label}</td>
                <td className="num">{data[field.key] ?? "—"}</td>
                <td>{data.source ?? "—"}</td>
                <td>{data.last_checked ?? "never"}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {data.notes && <p className="faint" style={{ marginTop: 12 }}>{data.notes}</p>}
      </div>
    </>
  );
}
