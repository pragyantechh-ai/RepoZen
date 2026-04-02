import { createContext, useContext, useState, type ReactNode } from "react";

interface RepoSummary {
  total_pages: number;
  languages: string[];
  files: string[];
}

interface SessionState {
  sessionId: string | null;
  status: "idle" | "analyzing" | "ready" | "error";
  message: string;
  progress: number;
  repoSummary: RepoSummary | null;
}

interface SessionContextValue extends SessionState {
  setSession: (id: string) => void;
  setStatus: (s: SessionState["status"]) => void;
  setMessage: (m: string) => void;
  setProgress: (p: number) => void;
  setRepoSummary: (r: RepoSummary | null) => void;
  reset: () => void;
}

const SessionContext = createContext<SessionContextValue | null>(null);

const INITIAL: SessionState = {
  sessionId: null,
  status: "idle",
  message: "",
  progress: 0,
  repoSummary: null,
};

export function SessionProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<SessionState>(INITIAL);

  const value: SessionContextValue = {
    ...state,
    setSession: (id) => setState((s) => ({ ...s, sessionId: id })),
    setStatus: (status) => setState((s) => ({ ...s, status })),
    setMessage: (message) => setState((s) => ({ ...s, message })),
    setProgress: (progress) => setState((s) => ({ ...s, progress })),
    setRepoSummary: (repoSummary) => setState((s) => ({ ...s, repoSummary })),
    reset: () => setState(INITIAL),
  };

  return (
    <SessionContext.Provider value={value}>{children}</SessionContext.Provider>
  );
}

export function useSession() {
  const ctx = useContext(SessionContext);
  if (!ctx) throw new Error("useSession must be used within <SessionProvider>");
  return ctx;
}