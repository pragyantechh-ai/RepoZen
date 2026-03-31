import { Upload, SendHorizonal } from "lucide-react";

const ChatInput = () => {
  return (
    <div className="w-full max-w-2xl mx-auto">
      <div
        className={[
          "relative flex items-center gap-3 px-5 py-4 rounded-2xl",
          "glass",
          "border border-border/40",
          "shadow-[0_10px_40px_-10px_rgba(0,0,0,0.6)]",
          "transition-all duration-300",
          "focus-within:border-primary/50",
        ].join(" ")}
      >
        {/* Upload */}
        <button className="relative text-muted-foreground hover:text-foreground transition-colors">
          <Upload className="h-5 w-5" />
        </button>

        {/* Input */}
        <input
          type="text"
          placeholder="Ask anything about your code..."
          className="flex-1 bg-transparent outline-none text-sm text-foreground placeholder:text-muted-foreground"
        />

        {/* Send Button */}
        <button className="relative w-10 h-10 rounded-xl flex items-center justify-center bg-gradient-to-br from-primary to-accent text-white shadow-md hover:scale-105 transition-all duration-200">
          <SendHorizonal className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
};

export default ChatInput;