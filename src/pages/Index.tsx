import { FolderCode, Brain, FlaskConical, Wrench } from "lucide-react";
import ActionCard from "@/components/ActionCard";
import ChatInput from "@/components/ChatInput";
import AppSidebar from "@/components/AppSidebar";
import Particles from "@/components/Particles";

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
    <div className="min-h-screen relative">
      <Particles />
      <AppSidebar />

      {/* Main content — offset for sidebar */}
      <main className="ml-16 flex flex-col items-center justify-center min-h-screen px-6">
        {/* Hero */}
        <div className="text-center mb-12 animate-fade-in">
          <h1 className="text-4xl md:text-5xl font-display font-bold mb-4">
            <span className="text-gradient">RepoZen</span>
          </h1>
          <p className="text-muted-foreground text-lg max-w-md mx-auto">
            AI-powered code intelligence for your repositories
          </p>
        </div>

        {/* Action Cards */}
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

        {/* Chat Input */}
        <ChatInput />
      </main>
    </div>
  );
};

export default Index;