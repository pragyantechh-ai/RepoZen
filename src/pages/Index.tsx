import {
  Sparkles,
  FolderCode,
  Brain,
  FlaskConical,
  Wrench,
  Github,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import ActionCard from "@/components/ActionCard";
import ChatInput from "@/components/ChatInput";
import Particles from "@/components/Particles";
import AppSidebar from "@/components/AppSidebar";

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
  return (
    <div className="relative min-h-screen overflow-hidden bg-[hsl(var(--background))] flex">
      
      {/* Background Glow */}
      <div className="absolute inset-0 flex justify-center -z-10">
        <div className="w-[600px] h-[600px] bg-primary/20 blur-[140px] rounded-full mt-20" />
      </div>

      <Particles />
      <AppSidebar />

      {/* Top bar */}
      <header className="fixed top-0 right-0 left-16 z-20 flex items-center justify-end px-6 py-4">
        <Button
          variant="outline"
          size="sm"
          className="glass-card gap-2 text-xs font-medium border-border/40 hover:border-primary/40"
        >
          <Github className="h-4 w-4" />
          Connect GitHub
        </Button>
      </header>

      {/* MAIN */}
      <main className="flex-1 ml-16 flex items-center justify-center px-6">
        
        {/* CONTENT WRAPPER (THIS WAS MISSING) */}
        <div className="w-full max-w-5xl flex flex-col items-center text-center">
          
          {/* HERO */}
          <div className="mb-14 flex flex-col items-center">
            
            <div className="relative mb-6">
              <div className="w-14 h-14 rounded-2xl bg-primary/20 flex items-center justify-center glow-primary">
                <Sparkles className="h-6 w-6 text-primary" />
              </div>
            </div>

            <h1 className="font-display text-5xl font-semibold tracking-tight">
              AI Engineering{" "}
              <span className="text-gradient">Copilot</span>
            </h1>

            <p className="mt-4 text-muted-foreground text-base max-w-xl leading-relaxed">
              Understand, analyze, and generate code from your repository
            </p>
          </div>

          {/* ACTION CARDS */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 w-full mb-14">
            {actions.map((action, i) => (
              <ActionCard
                key={action.title}
                {...action}
                delay={i * 100}
              />
            ))}
          </div>

          {/* INPUT */}
          <ChatInput />

        </div>
      </main>
    </div>
  );
};

export default Index;