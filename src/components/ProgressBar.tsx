import { CheckCircle2, XCircle, Loader2 } from "lucide-react";
import { useSessionStore } from "@/stores/sessionStore";

const AnalysisProgress = () => {
  const { status, message, progress, repoSummary } = useSessionStore();

  if (status === "idle") return null;

  return (
    <div className="w-full max-w-2xl mx-auto mb-8 animate-fade-in">
      <div className="glass-card rounded-2xl p-5">
        {/* Header row */}
        <div className="flex items-center gap-3 mb-4">
          {status === "analyzing" && (
            <Loader2 className="h-5 w-5 text-primary animate-spin" />
          )}
          {status === "ready" && (
            <CheckCircle2 className="h-5 w-5 text-emerald-400" />
          )}
          {status === "error" && (
            <XCircle className="h-5 w-5 text-red-400" />
          )}
          <span className="text-sm font-medium text-foreground">
            {message}
          </span>
        </div>

        {/* Progress bar */}
        <div className="w-full h-2 rounded-full bg-secondary/60 overflow-hidden">
          <div
            className={[
              "h-full rounded-full transition-all duration-700 ease-out",
              status === "error"
                ? "bg-red-500"
                : status === "ready"
                ? "bg-gradient-to-r from-emerald-400 to-teal-400"
                : "bg-gradient-to-r from-primary to-accent",
            ].join(" ")}
            style={{ width: `${progress}%` }}
          />
        </div>

        {/* Progress text */}
        <div className="flex items-center justify-between mt-2">
          <span className="text-xs text-muted-foreground">
            {status === "analyzing" && "Parsing files, building index..."}
            {status === "ready" && "Analysis complete"}
            {status === "error" && "Analysis failed"}
          </span>
          <span className="text-xs text-muted-foreground">
            {Math.round(progress)}%
          </span>
        </div>

        {/* Repo summary — shown when ready */}
        {status === "ready" && repoSummary && (
          <div className="mt-4 pt-4 border-t border-border/30 flex gap-6 text-xs text-muted-foreground">
            <span>
              <strong className="text-foreground">{repoSummary.total_pages}</strong> pages
            </span>
            <span>
              <strong className="text-foreground">{repoSummary.files.length}</strong> files
            </span>
            <span>
              {repoSummary.languages.map((lang) => (
                <span
                  key={lang}
                  className="inline-block px-2 py-0.5 rounded-full bg-primary/15 text-primary text-[11px] mr-1"
                >
                  {lang}
                </span>
              ))}
            </span>
          </div>
        )}
      </div>
    </div>
  );
};

export default AnalysisProgress;