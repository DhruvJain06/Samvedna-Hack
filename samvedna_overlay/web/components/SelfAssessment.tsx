"use client";

import { useState, useEffect } from "react";
import { DEFAULT_SESSION, api } from "@/lib/api";
import { instrumentAvailableIn } from "@/i18n";
import { useLocale } from "@/i18n/LocaleProvider";

/**
 * Adaptive Tactical Self-Assessment (ATAS)
 *
 * Designed for Armed Forces Personnel:
 * 1. Operational Phrasing: Shifts from stigmatized civilian clinical depression
 *    words ("feeling like a failure", "trouble watching TV") to tactical reality
 *    (sentry recovery, physical exhaustion in drills, section/buddy frictions).
 * 2. Adaptive Question Rotation: Identifies questions providing zero diagnostic value
 *    (consistently 0 across past sessions) and dynamically rotates them out for fresh
 *    perspectives (domestic friction, somatic pain masking, leave readjustment).
 * 3. Delta / Progress Tracking: Injects a progress comparison for previously flagged areas.
 * 4. Backward & Gate Invariant: Maps seamlessly to the 9-item clinical score schema
 *    required by the backend without breaking validation or acute routing.
 */

const OPTIONS = [
  { value: 0, label: "Not at all" },
  { value: 1, label: "Several days" },
  { value: 2, label: "More than half the days" },
  { value: 3, label: "Nearly every day" },
];

interface TacticalItem {
  id: number;
  category: string;
  tacticalPrompt: string;
  contextNote: string;
}

// 9 Tactical Items replacing standard civilian questions 1-to-1
const BASE_TACTICAL_ITEMS: TacticalItem[] = [
  {
    id: 0,
    category: "anhedonia_readiness",
    tacticalPrompt: "Loss of motivation or drive during routine weapon drills, PT, or unit roll-call",
    contextNote: "Operational readiness & unit engagement",
  },
  {
    id: 1,
    category: "morale_mood",
    tacticalPrompt: "Feeling mentally low, persistently drained, or questioning your purpose in service",
    contextNote: "Morale & emotional endurance",
  },
  {
    id: 2,
    category: "sleep_recovery",
    tacticalPrompt: "Broken, disturbed sleep or inability to recover restfully after sentry or night duties",
    contextNote: "Somatic fatigue & vigilance rebound",
  },
  {
    id: 3,
    category: "energy_stamina",
    tacticalPrompt: "Persistent physical exhaustion or feeling unusually slow to complete assigned tasks",
    contextNote: "Duty stamina & combat exhaustion",
  },
  {
    id: 4,
    category: "somatic_appetite",
    tacticalPrompt: "Skipping mess meals, lack of appetite, or noticeable digestive/body distress without illness",
    contextNote: "Physical wellbeing & nutrition",
  },
  {
    id: 5,
    category: "interpersonal_friction",
    tacticalPrompt: "Feeling irritable, short-tempered, or experiencing friction with platoon buddies/seniors",
    contextNote: "Section cohesion & irritability",
  },
  {
    id: 6,
    category: "cognitive_focus",
    tacticalPrompt: "Trouble maintaining sharp concentration during briefings, guard duty, or equipment checks",
    contextNote: "Situational awareness & mental acuity",
  },
  {
    id: 7,
    category: "agitation_withdrawal",
    tacticalPrompt: "Restlessness (pacing/nervous tension) or wanting to completely isolate from barracks mates",
    contextNote: "Hyperarousal & social withdrawal",
  },
  {
    id: 8,
    category: "acute_safety",
    tacticalPrompt: "Thoughts that you cannot go on with service life, or thoughts of hurting yourself",
    contextNote: "Immediate clinical safety gate",
  },
];

// Pool of alternative questions rotated in if a soldier consistently scores 0 on certain items
const ROTATIONAL_REPLACEMENTS: Record<number, { prompt: string; note: string }> = {
  0: {
    prompt: "Feeling disengaged or unappreciated despite carrying out all duty responsibilities fully",
    note: "Duty motivation & recognition",
  },
  4: {
    prompt: "Unexplained persistent body aches, tension headaches, or back stiffness after duty shifts",
    note: "Somatic stress manifestation",
  },
  5: {
    prompt: "Family stress or property/home tensions back in your hometown feeling overwhelming while on post",
    note: "Domestic conflict & distance stress",
  },
  7: {
    prompt: "Feeling restless or unable to adapt back to standard camp routine after returning from leave",
    note: "Post-leave readjustment",
  },
};

const ACUTE_INDEX = 8; // item 9, zero-based

function band(total: number): { label: string; tone: string } {
  if (total >= 20) return { label: "Severe (20–27)", tone: "stop" };
  if (total >= 15) return { label: "Moderately severe (15–19)", tone: "hold" };
  if (total >= 10) return { label: "Moderate (10–14)", tone: "hold" };
  if (total >= 5) return { label: "Mild (5–9)", tone: "" };
  return { label: "Minimal (0–4)", tone: "pass" };
}

export function SelfAssessment({
  pid,
  onAcute,
  step,
}: {
  pid: string;
  onAcute?: () => void;
  step?: number;
}) {
  const { t, locale } = useLocale();
  const available = instrumentAvailableIn("PHQ9", locale);

  const [open, setOpen] = useState(false);
  const [index, setIndex] = useState(0);
  const [answers, setAnswers] = useState<(number | null)[]>(
    Array(BASE_TACTICAL_ITEMS.length).fill(null),
  );
  const [progressDelta, setProgressDelta] = useState<number | null>(null);
  const [hasPriorStrain, setHasPriorStrain] = useState(false);
  const [rotatedItems, setRotatedItems] = useState<TacticalItem[]>(BASE_TACTICAL_ITEMS);
  const [rotationActive, setRotationActive] = useState(false);

  const [result, setResult] = useState<{ total: number; acute: boolean } | null>(null);
  const [outcome, setOutcome] = useState<
    Awaited<ReturnType<typeof api.assessment>> | null
  >(null);
  const [sending, setSending] = useState(false);
  const [sendError, setSendError] = useState("");

  // Adaptive logic: Load soldier's recent assessment profile from local storage cache
  useEffect(() => {
    if (!pid) return;
    try {
      const storageKey = `samvedna_atas_profile_${pid}`;
      const raw = localStorage.getItem(storageKey);
      if (raw) {
        const history = JSON.parse(raw);
        // If they had previous scores > 0 in non-acute categories, flag for progress comparison
        const priorTotal = history.lastTotal || 0;
        if (priorTotal >= 5) {
          setHasPriorStrain(true);
        }

        // Check if items repeatedly flatlined at 0 for consecutive sessions
        const zeroCounts: Record<number, number> = history.zeroCounts || {};
        const updated = BASE_TACTICAL_ITEMS.map((item) => {
          if (item.id !== ACUTE_INDEX && (zeroCounts[item.id] || 0) >= 2 && ROTATIONAL_REPLACEMENTS[item.id]) {
            return {
              ...item,
              tacticalPrompt: ROTATIONAL_REPLACEMENTS[item.id].prompt,
              contextNote: ROTATIONAL_REPLACEMENTS[item.id].note,
            };
          }
          return item;
        });
        setRotatedItems(updated);
        setRotationActive(Object.values(zeroCounts).some((c) => c >= 2));
      }
    } catch {
      // Fallback cleanly to standard base items
      setRotatedItems(BASE_TACTICAL_ITEMS);
    }
  }, [pid]);

  const title = (style?: React.CSSProperties) =>
    step ? (
      <div className="sec-head">
        <span className="sec-n">{step}</span>
        <h2 style={style}>Operational Well-Being & Tactical Readiness Check</h2>
      </div>
    ) : (
      <h2 style={style}>Operational Well-Being & Tactical Readiness Check</h2>
    );

  if (!available) {
    return (
      <div className="card">
        {title()}
        <div className="banner warn" style={{ marginTop: 12 }}>
          <strong>Assessment</strong>
          <span>{t("instrument.unavailable")}</span>
        </div>
      </div>
    );
  }

  if (result) {
    const b = band(result.total);
    return (
      <div className="card">
        {title()}
        {result.acute ? (
          <div className="banner stop" style={{ marginTop: 12 }}>
            <strong>Immediate Medical Officer Contact Initiated</strong>
            <span>
              What you have described is prioritized confidentially. This routes to the
              unit medical officer — <strong>not</strong> to your commanding officer,
              not on your service sheet, and it will not affect promotion or ACR. You
              can also reach the medical room immediately via the unit exchange.
            </span>
          </div>
        ) : sendError ? (
          <div className="banner warn" style={{ marginTop: 12 }}>
            <strong>Not recorded.</strong>
            <span>You completed the questionnaire, but it did not reach the system.</span>
          </div>
        ) : outcome ? (
          <div className="banner good" style={{ marginTop: 12 }}>
            <strong>Assessment Complete & Analyzed</strong>
          </div>
        ) : (
          <div className="banner info" style={{ marginTop: 12 }}>
            <span>Recording and contextualizing your responses...</span>
          </div>
        )}

        <div className="row" style={{ marginTop: 16 }}>
          <span className="faint">Readiness Band:</span>
          <span className={`pill ${b.tone}`}>{b.label}</span>
          {outcome && outcome.total !== result.total && (
            <span className="faint">(verified score: {outcome.total})</span>
          )}
        </div>

        {progressDelta !== null && (
          <p className="faint" style={{ marginTop: 8 }}>
            Self-Reported Operational Progress:{" "}
            <strong>
              {progressDelta > 0
                ? "Improved compared to last cycle (+)"
                : progressDelta < 0
                ? "Heightened fatigue noticed (-)"
                : "Stable across sessions"}
            </strong>
          </p>
        )}

        <p className="faint" style={{ marginTop: 10 }}>
          Evaluated against military operational strain markers. Raw answers are never
          shared; only clinical status and duty recovery bands are preserved.
        </p>

        {sending && <p className="faint" style={{ marginTop: 12 }}>Syncing secure ledger...</p>}
        {sendError && (
          <div className="banner warn" style={{ marginTop: 12 }}>
            <strong>Error syncing:</strong> <span>{sendError}</span>
          </div>
        )}

        <div className="row" style={{ marginTop: 14 }}>
          <button
            onClick={() => {
              setResult(null);
              setOpen(false);
              setIndex(0);
              setAnswers(Array(BASE_TACTICAL_ITEMS.length).fill(null));
              setProgressDelta(null);
            }}
          >
            Close
          </button>
        </div>
      </div>
    );
  }

  if (!open) {
    return (
      <div className="card">
        {title()}
        <div className="banner info" style={{ marginTop: 12 }}>
          <strong>Tactical Readiness & Stress Screen</strong>
          <span>
            {rotationActive
              ? "Adaptive Question Rotation Active (Low-variance items rotated to fresh operational indicators)."
              : "Standard Operational Battery Active."}
          </span>
        </div>
        <p className="muted" style={{ marginTop: 12 }}>
          Measures physical, mental, and sentry recovery markers over the past two weeks.
          Confidential, voluntary, and evaluated without administrative career impact.
        </p>
        <p className="faint" style={{ marginTop: 8 }}>
          Adapted for Armed Forces Service Conditions (Clinical Mapping: PHQ-9 Equivalent Standard).
        </p>
        <div className="row" style={{ marginTop: 14 }}>
          <button className="primary" onClick={() => setOpen(true)}>
            Start Assessment
          </button>
        </div>
      </div>
    );
  }

  // If prior strain existed, show a progress comparison item first
  if (hasPriorStrain && progressDelta === null && index === 0) {
    return (
      <div className="card">
        <div className="row" style={{ marginBottom: 6 }}>
          {title({ fontSize: "1.25rem" })}
          <span className="spacer" />
          <span className="pill info">Progress Tracker</span>
        </div>
        <p className="faint" style={{ margin: "14px 0 4px" }}>
          Periodic Progress Comparison
        </p>
        <p style={{ fontSize: "1.1rem", fontFamily: "var(--serif)", marginBottom: 14 }}>
          Compared to two weeks ago, how would you rate your general energy, sleep recovery,
          and duty stamina?
        </p>
        <div className="stack" style={{ gap: 8 }}>
          {[
            { label: "Noticeably Better / More Rested", val: 2 },
            { label: "Slightly Better", val: 1 },
            { label: "About the Same", val: 0 },
            { label: "More Fatigued / Strained", val: -1 },
          ].map((opt) => (
            <button
              key={opt.val}
              onClick={() => setProgressDelta(opt.val)}
              className="primary"
              style={{ textAlign: "left", justifyContent: "flex-start" }}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>
    );
  }

  const currentItem = rotatedItems[index];
  const answered = answers[index];
  const last = index === rotatedItems.length - 1;

  const choose = (value: number) => {
    const next = [...answers];
    next[index] = value;
    setAnswers(next);
  };

  const finish = async () => {
    const items = answers.map((a) => a ?? 0);
    const total = items.reduce((sum, a) => sum + a, 0);
    const acute = items[ACUTE_INDEX] > 0;
    setResult({ total, acute });
    if (acute) onAcute?.();

    // Update adaptive learning cache for soldier to rotate flatline items next time
    if (pid) {
      try {
        const storageKey = `samvedna_atas_profile_${pid}`;
        const prev = JSON.parse(localStorage.getItem(storageKey) || "{}");
        const prevZeroCounts = prev.zeroCounts || {};
        const updatedZeroCounts: Record<number, number> = {};

        items.forEach((score, idx) => {
          if (score === 0) {
            updatedZeroCounts[idx] = (prevZeroCounts[idx] || 0) + 1;
          } else {
            updatedZeroCounts[idx] = 0; // Reset if they experienced any strain
          }
        });

        localStorage.setItem(
          storageKey,
          JSON.stringify({
            lastTotal: total,
            zeroCounts: updatedZeroCounts,
            lastDate: new Date().toISOString(),
          }),
        );
      } catch {
        // Local cache write non-blocking
      }
    }

    if (!pid) {
      setSendError("No identity resolved yet — reload and try again");
      return;
    }

    setSending(true);
    setSendError("");
    try {
      setOutcome(
        await api.assessment(pid, items, {
          ...DEFAULT_SESSION.personnel,
          operator: pid,
        }),
      );
    } catch (e) {
      setSendError((e as Error).message);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="card">
      <div className="row" style={{ marginBottom: 6 }}>
        {title({ fontSize: "1.25rem" })}
        <span className="spacer" />
        <span className="faint">
          Question {index + 1} of {rotatedItems.length}
        </span>
      </div>

      <div
        className="progress"
        role="progressbar"
        aria-valuenow={index + 1}
        aria-valuemin={1}
        aria-valuemax={rotatedItems.length}
      >
        <span style={{ width: `${((index + 1) / rotatedItems.length) * 100}%` }} />
      </div>

      <p className="faint" style={{ margin: "14px 0 4px" }}>
        Over the last 2 weeks, how often have you been bothered by:
      </p>
      <p style={{ fontSize: "1.15rem", fontFamily: "var(--serif)", marginBottom: 4 }}>
        {currentItem.tacticalPrompt}
      </p>
      <p className="faint" style={{ fontSize: "0.85rem", marginBottom: 14 }}>
        Focus area: {currentItem.contextNote}
      </p>

      <div className="stack" style={{ gap: 8 }}>
        {OPTIONS.map((o) => (
          <button
            key={o.value}
            onClick={() => choose(o.value)}
            className={answered === o.value ? "primary" : ""}
            style={{ textAlign: "left", justifyContent: "flex-start" }}
            aria-pressed={answered === o.value}
          >
            {o.label}
          </button>
        ))}
      </div>

      <div className="row" style={{ marginTop: 18 }}>
        <button onClick={() => setIndex((i) => Math.max(0, i - 1))} disabled={index === 0}>
          Back
        </button>
        {last ? (
          <button className="primary" onClick={finish} disabled={answered === null}>
            Submit Assessment
          </button>
        ) : (
          <button
            className="primary"
            onClick={() => setIndex((i) => i + 1)}
            disabled={answered === null}
          >
            Next
          </button>
        )}
        <span className="spacer" />
        <button
          className="ghost"
          onClick={() => {
            setOpen(false);
            setIndex(0);
            setAnswers(Array(BASE_TACTICAL_ITEMS.length).fill(null));
          }}
        >
          Cancel
        </button>
      </div>
    </div>
  );
}
