import { useState } from "react";
import { X, Github, Loader2 } from "lucide-react";

interface UploadModalProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (url: string) => void;
  loading: boolean;
}

const UploadModal = ({ open, onClose, onSubmit, loading }: UploadModalProps) => {
  const [url, setUrl] = useState("");

  if (!open) return null;

  const handleSubmit = () => {
    const trimmed = url.trim();
    if (!trimmed) return;
    onSubmit(trimmed);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !loading) handleSubmit();
    if (e.key === "Escape") onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative glass rounded-2xl p-6 w-full max-w-md mx-4 animate-fade-in">
        {/* Close */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-muted-foreground hover:text-foreground transition-colors"
        >
          <X className="h-4 w-4" />
        </button>

        {/* Header */}
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-indigo-500 flex items-center justify-center">
            <Github className="h-5 w-5 text-white" />
          </div>
          <div>
            <h2 className="text-lg font-display font-semibold text-foreground">
              Upload Repository
            </h2>
            <p className="text-sm text-muted-foreground">
              Paste a GitHub repo URL to analyze
            </p>
          </div>
        </div>

        {/* Input */}
        <input
          type="text"
          placeholder="https://github.com/user/repo.git"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={loading}
          autoFocus
          className="w-full px-4 py-3 rounded-xl bg-secondary/60 border border-border/40 text-sm text-foreground placeholder:text-muted-foreground outline-none focus:border-primary/50 transition-colors disabled:opacity-50"
        />

        {/* Submit */}
        <button
          onClick={handleSubmit}
          disabled={!url.trim() || loading}
          className="w-full mt-4 py-3 rounded-xl bg-gradient-to-r from-primary to-accent text-white font-medium text-sm flex items-center justify-center gap-2 hover:scale-[1.02] transition-all disabled:opacity-50 disabled:hover:scale-100"
        >
          {loading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Uploading...
            </>
          ) : (
            "Analyze Repository"
          )}
        </button>
      </div>
    </div>
  );
};

export default UploadModal;