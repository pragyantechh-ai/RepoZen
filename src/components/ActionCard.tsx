import { cn } from "@/lib/utils";
import type { LucideIcon } from "lucide-react";

interface ActionCardProps {
  title: string;
  description: string;
  icon: LucideIcon;
  gradient: string;
  delay: number;
}

const ActionCard = ({
  title,
  description,
  icon: Icon,
  gradient,
  delay,
}: ActionCardProps) => {
  return (
    <button
      className={cn(
        "group relative flex flex-col gap-4 rounded-2xl p-6 text-left",
        "glass-card",
        "border border-border/40",
        "transition-all duration-300",
        "hover:scale-[1.04]",
        "hover:border-primary/40",
        "opacity-0 animate-fade-in"
      )}
      style={{
        animationDelay: `${delay}ms`,
        animationFillMode: "forwards",
      }}
    >
      {/* Hover Glow */}
      <div className="absolute inset-0 rounded-2xl opacity-0 group-hover:opacity-100 transition duration-300 pointer-events-none">
        <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-primary/10 via-transparent to-accent/10 blur-xl" />
      </div>

      {/* Icon */}
      <div
        className={cn(
          "relative rounded-xl p-3 w-fit shadow-md",
          gradient
        )}
      >
        <Icon className="h-5 w-5 text-white" />
      </div>

      {/* Content */}
      <div className="relative">
        <h3 className="font-display font-semibold text-base text-foreground">
          {title}
        </h3>
        <p className="text-sm text-muted-foreground mt-1 leading-relaxed">
          {description}
        </p>
      </div>
    </button>
  );
};

export default ActionCard;