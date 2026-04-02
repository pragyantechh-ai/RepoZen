import { FolderCode, Brain, FlaskConical, Wrench } from "lucide-react";
import ActionCard from "../components/ActionCard";
import ChatInput from "../components/ChatInput";
import AppSidebar from "../components/AppSidebar";
import Particles from "../components/Particles";
import AnalysisProgress from "../components/ProgressBar";
import ChatArea from "../components/ChatArea";
import { useSession } from "../stores/sessionStore";

const actions = [
  {
    title: "Analyze Repository",
    description: "Deep scan your codebase structure and dependencies",
    icon: FolderCode,
    gradient: "bg-gradient-to-br from-purple-500 to-indigo-500",
  },
  {
    title: "Explain Codebase",
    description: "Get AI-powered explanations of any module or function",
    icon: Brain,
    gradient: "bg-gradient-to-br from-blue-500 to-cyan-500",
  },
  {
    title: "Generate Tests",
    description: "Auto-generate unit and integration test suites",
    icon: FlaskConical,
    gradient: "bg-gradient-to-br from-emerald-500 to-teal-500",
  },
  {
    title: "Modify Code",
    description: "Refactor, optimize, and transform code with AI",
    icon: Wrench,
    gradient: "bg-gradient-to-br from-orange-500 to-amber-500",
  },
];

const Index = () => {
  const { status, messages } = useSession();
  const isChatMode = messages.length > 0;

  console.log("[Index] render — status:", status, "messages:", messages.length, "chatMode:", isChatMode);

  // ── CHAT MODE ──────────────────────────────────────────────────
  if (isChatMode) {
    return (
      <div className="h-screen flex relative overflow-hidden">
        <Particles />
        <AppSidebar />

        <div className="ml-16 flex-1 flex flex-col h-screen">
          {/* Compact header */}
          <div
            className="shrink-0 flex items-center gap-3 px-6 py-3 z-10"
            style={{
              background: "hsla(228, 20%, 6%, 0.8)",
              backdropFilter: "blur(12px)",
              borderBottom: "1px solid hsla(228,15%,22%,0.2)",
            }}
          >
            <h1 className="text-lg font-bold">
              <span className="text-gradient">RepoZen</span>
            </h1>
            <div
              style={{
                width: "1px",
                height: "16px",
                background: "hsla(228,15%,22%,0.4)",
              }}
            />
            <span className="text-xs text-muted-foreground">
              Chat &middot; Session active
            </span>
          </div>

          {/* Chat messages — scrollable */}
          <ChatArea />

          {/* Input pinned bottom */}
          <div
            className="shrink-0"
            style={{
              background: "hsla(228, 20%, 6%, 0.6)",
              backdropFilter: "blur(12px)",
              borderTop: "1px solid hsla(228,15%,22%,0.15)",
            }}
          >
            <ChatInput />
          </div>
        </div>
      </div>
    );
  }

  // ── LANDING MODE ───────────────────────────────────────────────
  return (
    <div className="h-screen flex relative overflow-hidden">
      <Particles />
      <AppSidebar />

      <div className="ml-16 flex-1 flex flex-col items-center justify-center px-6">
        {/* Hero */}
        <div className="text-center mb-12 animate-fade-in">
          <h1 className="text-4xl md:text-5xl font-bold mb-4">
            <span className="text-gradient">RepoZen</span>
          </h1>
          <p className="text-muted-foreground text-lg max-w-md mx-auto">
            AI-powered code intelligence for your repositories
          </p>
        </div>

        {/* Action Cards — idle only */}
        {status === "idle" && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 w-full max-w-4xl mb-12">
            {actions.map((action, i) => (
              <ActionCard
                key={action.title}
                title={action.title}
                description={action.description}
                icon={action.icon}
                gradient={action.gradient}
                delay={200 + i * 100}
              />
            ))}
          </div>
        )}

        {/* Progress bar */}
        <AnalysisProgress />

        {/* Chat Input */}
        <ChatInput />
      </div>
    </div>
  );
};

export default Index;