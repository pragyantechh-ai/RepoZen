import { FolderGit2, Clock, Settings, Sparkles } from "lucide-react";

const sidebarItems = [
  { icon: Sparkles, label: "AI" },
  { icon: FolderGit2, label: "Projects" },
  { icon: Clock, label: "History" },
  { icon: Settings, label: "Settings" },
];

const AppSidebar = () => {
  return (
    <aside className="fixed left-0 top-0 h-full w-16 glass flex flex-col items-center py-6 gap-1 z-30">
      <div className="w-8 h-8 rounded-lg bg-primary/20 flex items-center justify-center mb-6">
        <Sparkles className="h-4 w-4 text-primary" />
      </div>
      <div className="flex-1 flex flex-col items-center gap-2">
        {sidebarItems.map((item) => (
          <button
            key={item.label}
            title={item.label}
            className="w-10 h-10 rounded-xl flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-secondary/60 transition-colors duration-200"
          >
            <item.icon className="h-[18px] w-[18px]" />
          </button>
        ))}
      </div>
    </aside>
  );
};

export default AppSidebar;