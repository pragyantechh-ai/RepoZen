import { CheckCircle2, XCircle, Loader2 } from "lucide-react";
import { useSession } from "../stores/sessionStore";

const AnalysisProgress = () => {
  const { status, message, progress, repoSummary } = useSession();

  if (status === "idle") return null;

  const barColor =
    status === "error"
      ? "bg-red-500"
      : status === "ready"
      ? "bg-gradient-to-r from-emerald-400 to-teal-400"
      : "bg-gradient-to-r from-purple-500 to-blue-500";

  return (
    <div className="w-full max-w-2xl mx-auto mb-8 animate-fade-in">
      <div
        className="rounded-2xl p-5"
        style={{
          background: "hsla(228, 20%, 12%, 0.4)",
          backdropFilter: "blur(24px)",
          border: "1px solid hsla(228, 15%, 22%, 0.2)",
        }}
      >
        <div className="flex items-center gap-3 mb-4">
          {status === "analyzing" && (
            <Loader2 className="h-5 w-5 text-purple-400 animate-spin shrink-0" />
          )}
          {status === "ready" && (
            <CheckCircle2 className="h-5 w-5 text-emerald-400 shrink-0" />
          )}
          {status === "error" && (
            <XCircle className="h-5 w-5 text-red-400 shrink-0" />
          )}
          <span className="text-sm font-medium text-foreground">{message}</span>
        </div>

        <div
          className="w-full h-2 rounded-full overflow-hidden"
          style={{ background: "hsla(228, 20%, 15%, 0.6)" }}
        >
          <div
            className={`h-full rounded-full transition-all duration-700 ease-out ${barColor}`}
            style={{ width: `${progress}%` }}
          />
        </div>

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

        {status === "ready" && repoSummary && (
          <div
            className="mt-4 pt-4 flex flex-wrap gap-4 text-xs text-muted-foreground"
            style={{ borderTop: "1px solid hsla(228,15%,22%,0.3)" }}
          >
            <span>
              <strong className="text-foreground">{repoSummary.total_pages}</strong> pages
            </span>
            <span>
              <strong className="text-foreground">{repoSummary.files.length}</strong> files
            </span>
            <span className="flex flex-wrap gap-1">
              {repoSummary.languages.map((lang) => (
                <span
                  key={lang}
                  className="inline-block px-2 py-0.5 rounded-full bg-purple-500/15 text-purple-300"
                  style={{ fontSize: "11px" }}
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