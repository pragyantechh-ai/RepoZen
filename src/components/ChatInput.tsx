import { useState, useRef, useCallback, useEffect } from "react";
import { Upload, SendHorizonal } from "lucide-react";
import UploadModal from "./UploadModal";
import { uploadRepoUrl, checkStatus } from "../services/api_service";
import { useSession } from "../stores/sessionStore";

const POLL_INTERVAL = 2000;

const ChatInput = () => {
  const [modalOpen, setModalOpen] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [query, setQuery] = useState("");
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const {
    sessionId,
    status,
    setSession,
    setStatus,
    setMessage,
    setProgress,
    setRepoSummary,
  } = useSession();

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  const startPolling = useCallback(
    (sid: string) => {
      let fakeProg = 10;

      pollRef.current = setInterval(async () => {
        try {
          const res = await checkStatus(sid);

          if (res.status === "ready") {
            if (pollRef.current) clearInterval(pollRef.current);
            setProgress(100);
            setStatus("ready");
            setMessage(res.message);
            setRepoSummary(res.repo_summary);
          } else if (res.status === "error") {
            if (pollRef.current) clearInterval(pollRef.current);
            setProgress(100);
            setStatus("error");
            setMessage(res.message);
          } else {
            fakeProg = Math.min(fakeProg + Math.random() * 12, 90);
            setProgress(fakeProg);
            setMessage(res.message);
          }
        } catch {
          console.warn("Status poll failed, retrying...");
        }
      }, POLL_INTERVAL);
    },
    [setProgress, setStatus, setMessage, setRepoSummary]
  );

  const handleUpload = useCallback(
    async (url: string) => {
      setUploading(true);
      try {
        const res = await uploadRepoUrl(url);
        setSession(res.session_id);
        setStatus("analyzing");
        setMessage(res.message);
        setProgress(5);
        setModalOpen(false);
        startPolling(res.session_id);
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : "Upload failed";
        setStatus("error");
        setMessage(msg);
      } finally {
        setUploading(false);
      }
    },
    [setSession, setStatus, setMessage, setProgress, startPolling]
  );

  const handleSend = () => {
    if (!query.trim() || !sessionId || status !== "ready") return;
    console.log("Send:", query, "session:", sessionId);
    setQuery("");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const canChat = status === "ready" && !!sessionId;

  return (
    <>
      <div className="w-full max-w-2xl mx-auto">
        <div
          className="relative flex items-center gap-3 px-5 py-4 rounded-2xl transition-all duration-300"
          style={{
            background: "hsla(228, 20%, 12%, 0.6)",
            backdropFilter: "blur(20px)",
            border: "1px solid hsla(228, 15%, 22%, 0.3)",
            boxShadow: "0 10px 40px -10px rgba(0,0,0,0.6)",
          }}
        >
          <button
            onClick={() => setModalOpen(true)}
            title="Upload repository"
            className="text-muted-foreground hover:text-foreground transition-colors"
          >
            <Upload className="h-5 w-5" />
          </button>

          <input
            type="text"
            placeholder={
              canChat
                ? "Ask anything about your code..."
                : "Upload a repository first..."
            }
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={!canChat}
            className="flex-1 bg-transparent outline-none text-sm text-foreground placeholder:text-muted-foreground disabled:opacity-40"
          />

          <button
            onClick={handleSend}
            disabled={!canChat || !query.trim()}
            className="w-10 h-10 rounded-xl flex items-center justify-center bg-gradient-to-br from-purple-500 to-blue-500 text-white shadow-md hover:scale-105 transition-all duration-200 disabled:opacity-40 disabled:hover:scale-100"
          >
            <SendHorizonal className="h-4 w-4" />
          </button>
        </div>
      </div>

      <UploadModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onSubmit={handleUpload}
        loading={uploading}
      />
    </>
  );
};

export default ChatInput;