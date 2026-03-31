import { create } from "zustand";

interface SessionState {
  sessionId: string | null;
  status: "idle" | "analyzing" | "ready" | "error";
  message: string;
  progress: number;
  repoSummary: {
    total_pages: number;
    languages: string[];
    files: string[];
  } | null;

  setSession: (id: string) => void;
  setStatus: (status: SessionState["status"]) => void;
  setMessage: (msg: string) => void;
  setProgress: (p: number) => void;
  setRepoSummary: (s: SessionState["repoSummary"]) => void;
  reset: () => void;
}

export const useSessionStore = create<SessionState>((set) => ({
  sessionId: null,
  status: "idle",
  message: "",
  progress: 0,
  repoSummary: null,

  setSession: (id) => set({ sessionId: id }),
  setStatus: (status) => set({ status }),
  setMessage: (message) => set({ message }),
  setProgress: (progress) => set({ progress }),
  setRepoSummary: (repoSummary) => set({ repoSummary }),
  reset: () =>
    set({
      sessionId: null,
      status: "idle",
      message: "",
      progress: 0,
      repoSummary: null,
    }),
}));