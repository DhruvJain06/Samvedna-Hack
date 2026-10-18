"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useLocale } from "@/i18n/LocaleProvider";
import { useSession } from "@/lib/session";

type WelfareItem = {
  scheme_name: string;
  type: string;
  contact?: string;
  url?: string;
};

const TYPE_CLASS: Record<string, string> = {
  helpline: "helpline",
  centre: "centre",
  circular: "circular",
  scheme: "scheme",
};

export function WelfareDirectory() {
  const { session } = useSession();
  const { t } = useLocale();
  const [items, setItems] = useState<WelfareItem[] | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!session) return;
    api
      .welfareDirectory(session)
      .then((body) => setItems(body.items))
      .catch(() => setError(true));
  }, [session]);

  if (error) {
    return <p className="banner stop" style={{ marginTop: 12 }}>{t("welfare.error")}</p>;
  }
  if (!items) {
    return (
      <div className="welfare-skel" aria-busy="true">
        <div className="skel" />
        <div className="skel" />
        <div className="skel" />
        <p className="faint">{t("welfare.loading")}</p>
      </div>
    );
  }
  if (items.length === 0) {
    return <p className="faint" style={{ marginTop: 12 }}>{t("welfare.empty")}</p>;
  }

  return (
    <ul className="welfare-list">
      {items.map((item) => (
        <li key={`${item.scheme_name}-${item.url ?? item.contact ?? ""}`} className="card welfare-card">
          <div className="row" style={{ alignItems: "center", gap: 8 }}>
            <strong>{item.scheme_name}</strong>
            <span className={`welfare-badge ${TYPE_CLASS[item.type] ?? "scheme"}`}>{item.type}</span>
          </div>
          {item.contact && <p className="faint" style={{ marginTop: 6 }}>{item.contact}</p>}
          {item.url && (
            <p style={{ marginTop: 8 }}>
              <a href={item.url} target="_blank" rel="noreferrer">
                {item.url}
              </a>
            </p>
          )}
        </li>
      ))}
    </ul>
  );
}
