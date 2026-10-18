"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { authApi, setDemoTransport } from "./api";
import type { Account, AuthConfig, Role, Session } from "./api";

/**
 * Who you are signed in as, and what that lets you reach.
 *
 * The roles here mirror the server's grant table exactly, because the whole
 * point of this system is the disclosure boundary and a console that let you
 * *see* something the API would refuse would be lying about it. So the UI hides
 * nothing it cannot also prove: every console page still calls the API, and a
 * role that should not have it gets a real 403 from the server rather than a
 * blank screen from the client.
 *
 * Two ways in, with a switch between them on the sign-in page:
 *
 * - **Username and password.** The server checks the password and sets an
 *   HttpOnly session cookie. The actor here is whatever `/api/auth/me` says the
 *   cookie belongs to; nothing the browser stores can change the role or scope.
 * - **Quick demo.** The original role chooser, for putting on each hat in turn.
 *   It identifies by plain headers, so the *server* decides whether it is
 *   allowed (`SAMVEDNA_DEMO_LOGIN`, REPLAY only). When the server says no, the
 *   switch is shown disabled rather than offered.
 */

export interface Actor {
  role: Role;
  operator: string;
  units: string;
  title: string;
  who: string;
  /** What this actor can reach. Mirrors the server's (role, purpose) grants. */
  routes: string[];
  canSee: string[];
  cannotSee: string[];
  accent: string;
}

export const ACTORS: Actor[] = [
  {
    role: "welfare_officer",
    operator: "WO-12",
    // Fallback only. Overwritten at runtime from /api/run — see
    // SessionProvider. Left as a neutral placeholder rather than a real
    // unit id, so a stale value is obviously stale.
    units: "UNIT-01,UNIT-02",
    title: "Welfare Officer",
    who: "Maj. R. Sharma · Welfare cell, UNIT-01 and UNIT-02",
    routes: ["/officer"],
    canSee: [
      "Escalated cases in your own units, with identity on request",
      "The gate arithmetic, the drivers, and the case against",
      "A recommended intervention, and a mandatory close-out",
      "Live welfare resources for the people you contact",
    ],
    cannotSee: [
      "Anyone under MONITOR — no name is produced at all",
      "Raw self-assessment answers, ever",
      "Cases in a unit you are not responsible for",
    ],
    accent: "var(--accent)",
  },
  {
    role: "commander",
    operator: "CO-01",
    units: "UNIT-01",
    title: "Commanding Officer",
    who: "Col. A. Menon · Officer Commanding, UNIT-01",
    routes: ["/unit"],
    canSee: [
      "Unit fatigue and workload heat maps, for rebalancing rosters",
      "Aggregates covering at least five personnel, with noise added",
    ],
    cannotSee: [
      "Any individual, ever — there is no drill-down and no API that answers one",
      "The welfare caseload",
      "Another unit's view",
    ],
    accent: "var(--mid)",
  },
  {
    role: "personnel",
    operator: "SELF",
    units: "",
    title: "Personnel",
    who: "A jawan or officer, viewing their own record",
    routes: ["/me"],
    canSee: [
      "Your own consent, per domain, in your own language",
      "The wellness self-assessment, if you choose to take it",
      "Why the system looked at you — the same reasons the officer got",
    ],
    cannotSee: [
      "Anybody else's anything",
      "The caseload, the unit view, or the ledger",
    ],
    accent: "var(--pass)",
  },
  {
    role: "auditor",
    operator: "AU-03",
    units: "",
    title: "Auditor",
    who: "Governance and audit · force-wide",
    routes: ["/audit", "/evidence", "/trust"],
    canSee: [
      "The full hash-chained ledger — every access, verdict, override and consent change",
      "The differential-privacy budget consumed",
      "That a person withdrew consent — and you are the only one who can",
      "Evidence baselines and nightly RBAC trust tests",
    ],
    cannotSee: [
      "The content of anything — only that an event occurred",
      "An identity. Reading the ledger never resolves a pid",
    ],
    accent: "var(--hold)",
  },
  {
    role: "mental_health_authority",
    operator: "MHA-1",
    // Force-wide. An acute referral routes to a clinician centrally.
    units: "",
    title: "Mental-Health Authority",
    who: "The designated clinician for acute referrals, force-wide",
    routes: ["/officer", "/evidence"],
    canSee: [
      "Acute referrals only — the cases the gates were bypassed for",
      "Identity on request, under the one purpose that permits it",
      "The gate values that were overridden, and why",
      "Read-only evidence baselines used by the model",
    ],
    cannotSee: [
      "Ordinary escalations — those belong to the unit welfare officer",
      "Anyone under MONITOR",
      "Aggregate unit views or the ledger",
    ],
    accent: "var(--stop)",
  },
];

const STORAGE_KEY = "samvedna.actor";
const METHOD_KEY = "samvedna.authMethod";

export type AuthMethod = "password" | "demo";

/** The account seeded for each role on first start. Shown as a hint on the
 *  sign-in page; the password is never in the source. */
export const DEMO_USERNAMES: Record<Role, string> = {
  welfare_officer: "wo12",
  commander: "co01",
  personnel: "personnel",
  auditor: "au03",
  mental_health_authority: "mha1",
};

interface SessionValue {
  actor: Actor | null;
  session: Session | null;
  /** Demo: become this role. Password: go to sign-in with it suggested. */
  signIn: (role: Role) => void;
  signOut: () => void;
  ready: boolean;
  /** Every actor, for the chooser and the "what others see" panels. */
  actors: Actor[];
  method: AuthMethod;
  setMethod: (method: AuthMethod) => void;
  /** What the server accepts. Null until it has answered. */
  config: AuthConfig | null;
  /** The signed-in account, in password mode. */
  account: Account | null;
  login: (username: string, password: string) => Promise<Actor>;
  /** Where a link to this role's console should go for the current method. */
  enterHref: (role: Role) => string;
}

const SessionContext = createContext<SessionValue | null>(null);

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [role, setRole] = useState<Role | null>(null);
  const [ready, setReady] = useState(false);
  // Units the current run actually covers, read from the public /api/run.
  //
  // These used to be literals on each actor: "UNIT-01,UNIT-02". Units were
  // later renamed to carry their service abbreviation — CRPF-01, IA-01 — and
  // the welfare officer console went quietly empty, because it was asking the
  // API about units that no longer existed and the API was correctly answering
  // "nothing there". Nothing errored; the caseload simply showed no cases,
  // which is indistinguishable from a quiet night.
  //
  // Deriving the scope from the run means renaming a unit, or switching the
  // deployment to a different service, cannot separate the two again.
  const [runUnits, setRunUnits] = useState<string[]>([]);

  useEffect(() => {
    fetch("/api/run")
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (Array.isArray(d?.units) && d.units.length > 0) setRunUnits(d.units);
      })
      .catch(() => { /* the literals below still apply */ });
  }, []);

  const [method, setMethodState] = useState<AuthMethod>("password");
  const [config, setConfig] = useState<AuthConfig | null>(null);
  const [account, setAccount] = useState<Account | null>(null);

  // Read after mount, so the server and first client render agree and the page
  // does not flash a role nobody chose. Asks the server which methods it
  // accepts, and who the session cookie belongs to, before declaring ready.
  useEffect(() => {
    let stored: string | null = null;
    let storedMethod: string | null = null;
    try {
      stored = window.localStorage.getItem(STORAGE_KEY);
      storedMethod = window.localStorage.getItem(METHOD_KEY);
    } catch {
      /* private browsing; the sign-in page still works for this session */
    }
    const fallback: AuthConfig = { password_login: false, demo_login: true, mode: "replay" };
    Promise.all([
      authApi.config().catch(() => fallback),
      authApi.me().catch(() => null),
    ]).then(([cfg, me]) => {
      setConfig(cfg);
      // A live session always wins: the person signed in with a password.
      let chosen: AuthMethod = "password";
      if (!me && cfg.demo_login && (storedMethod === "demo" || !cfg.password_login)) {
        chosen = "demo";
      }
      setMethodState(chosen);
      setDemoTransport(chosen === "demo");
      setAccount(me);
      if (chosen === "demo" && stored && ACTORS.some((a) => a.role === stored)) {
        setRole(stored as Role);
      }
      setReady(true);
    });
  }, []);

  const forgetDemoRole = useCallback(() => {
    setRole(null);
    try {
      window.localStorage.removeItem(STORAGE_KEY);
    } catch {
      /* nothing to clear */
    }
  }, []);

  const rememberMethod = (next: AuthMethod) => {
    try {
      window.localStorage.setItem(METHOD_KEY, next);
    } catch {
      /* the choice still applies for this session */
    }
  };

  const setMethod = useCallback((next: AuthMethod) => {
    if (next === "demo" && config && !config.demo_login) return;
    // Switching drops whoever was signed in under the other method, so the
    // two are never mixed — a demo role on top of a password session, or the
    // reverse, would make "who is this?" ambiguous.
    if (next === "demo") {
      void authApi.logout().catch(() => undefined);
      setAccount(null);
    } else {
      forgetDemoRole();
    }
    setMethodState(next);
    setDemoTransport(next === "demo");
    rememberMethod(next);
  }, [config, forgetDemoRole]);

  const signIn = useCallback((next: Role) => {
    if (method === "password") {
      // A role cannot be put on without its password. Send the person to
      // sign in, with that role's account suggested.
      window.location.assign(`/signin?role=${encodeURIComponent(next)}`);
      return;
    }
    setRole(next);
    try {
      window.localStorage.setItem(STORAGE_KEY, next);
    } catch {
      /* the choice still applies for this session */
    }
  }, [method]);

  const login = useCallback(async (username: string, password: string) => {
    const signedIn = await authApi.login(username, password);
    forgetDemoRole();
    setMethodState("password");
    setDemoTransport(false);
    setAccount(signedIn);
    rememberMethod("password");
    const base = ACTORS.find((a) => a.role === signedIn.role) ?? ACTORS[0];
    return { ...base, operator: signedIn.operator, units: signedIn.units };
  }, [forgetDemoRole]);

  const signOut = useCallback(() => {
    if (method === "password") {
      void authApi.logout().catch(() => undefined);
      setAccount(null);
      return;
    }
    forgetDemoRole();
  }, [method, forgetDemoRole]);

  // Roles whose authority is unit-scoped. Personnel and auditor are not:
  // personnel see only themselves, and the ledger is force-wide, so handing
  // either of them a unit list would widen what they can reach.
  const scoped = useMemo(
    () =>
      ACTORS.map((a) => {
        if (runUnits.length === 0) return a;
        if (a.role === "welfare_officer") {
          // A welfare cell covers more than one unit, so the first two.
          return { ...a, units: runUnits.slice(0, 2).join(",") };
        }
        if (a.role === "commander") {
          // A commanding officer holds exactly one.
          return { ...a, units: runUnits[0] };
        }
        return a;
      }),
    [runUnits],
  );

  const value = useMemo<SessionValue>(() => {
    let actor: Actor | null = null;
    if (method === "password" && account) {
      // The server's account decides role, operator and scope. The ACTORS
      // entry only supplies the wording for the panels.
      const base = scoped.find((a) => a.role === account.role);
      if (base) {
        actor = {
          ...base,
          operator: account.operator,
          units: account.units,
          title: account.title || base.title,
        };
      }
    } else if (method === "demo") {
      actor = scoped.find((a) => a.role === role) ?? null;
    }
    const enterHref = (r: Role) => {
      const route = scoped.find((a) => a.role === r)?.routes[0] ?? "/";
      if (method === "password" && actor?.role !== r) {
        return `/signin?role=${encodeURIComponent(r)}`;
      }
      return route;
    };
    return {
      actor,
      session: actor
        ? { role: actor.role, operator: actor.operator, units: actor.units }
        : null,
      signIn,
      signOut,
      ready,
      actors: scoped,
      method,
      setMethod,
      config,
      account,
      login,
      enterHref,
    };
  }, [role, signIn, signOut, ready, scoped, method, setMethod, config, account, login]);

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(): SessionValue {
  const context = useContext(SessionContext);
  if (!context) throw new Error("useSession must be used inside a SessionProvider");
  return context;
}

export function actorFor(role: Role): Actor | undefined {
  return ACTORS.find((a) => a.role === role);
}
