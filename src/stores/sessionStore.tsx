import { createContext, useContext, useState, useCallback, type ReactNode } from "react";

interface RepoSummary {
  total_pages: number;
  languages: string[];
  files: string[];
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  intent?: string;
  filesReferenced?: string[];
  timing?: Record<string, number>;
  timestamp: number;
}

interface SessionState {
  sessionId: string | null;
  status: "idle" | "analyzing" | "ready" | "error";
  message: string;
  progress: number;
  repoSummary: RepoSummary | null;
  messages: ChatMessage[];
  isGenerating: boolean;
}

interface SessionContextValue extends SessionState {
  setSession: (id: string) => void;
  setStatus: (s: SessionState["status"]) => void;
  setMessage: (m: string) => void;
  setProgress: (p: number) => void;
  setRepoSummary: (r: RepoSummary | null) => void;
  addMessage: (msg: ChatMessage) => void;
  setIsGenerating: (v: boolean) => void;
  reset: () => void;
}

const SessionContext = createContext<SessionContextValue | null>(null);

const INITIAL: SessionState = {
  sessionId: null,
  status: "idle",
  message: "",
  progress: 0,
  repoSummary: null,
  messages: [],
  isGenerating: false,
};

export function SessionProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<SessionState>({ ...INITIAL });

  const setSession = useCallback(
    (id: string) => setState((prev) => ({ ...prev, sessionId: id })),
    []
  );

  const setStatus = useCallback(
    (status: SessionState["status"]) => setState((prev) => ({ ...prev, status })),
    []
  );

  const setMessage = useCallback(
    (message: string) => setState((prev) => ({ ...prev, message })),
    []
  );

  const setProgress = useCallback(
    (progress: number) => setState((prev) => ({ ...prev, progress })),
    []
  );

  const setRepoSummary = useCallback(
    (repoSummary: RepoSummary | null) =>
      setState((prev) => ({ ...prev, repoSummary })),
    []
  );

  const addMessage = useCallback(
    (msg: ChatMessage) =>
      setState((prev) => {
        const newMessages = [...prev.messages, msg];
        console.log("[SessionContext] addMessage, total:", newMessages.length, "latest:", msg.role, msg.content.slice(0, 50));
        return { ...prev, messages: newMessages };
      }),
    []
  );

  const setIsGenerating = useCallback(
    (isGenerating: boolean) => setState((prev) => ({ ...prev, isGenerating })),
    []
  );

  const reset = useCallback(() => setState({ ...INITIAL, messages: [] }), []);

  const value: SessionContextValue = {
    ...state,
    setSession,
    setStatus,
    setMessage,
    setProgress,
    setRepoSummary,
    addMessage,
    setIsGenerating,
    reset,
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