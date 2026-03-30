import { Upload, SendHorizonal } from "lucide-react";

const ChatInput = () => {
  return (
    <div className="w-full max-w-2xl mx-auto">
      
      <div className="
        relative flex items-center gap-3 px-5 py-4 rounded-2xl
        glass border border-[hsl(var(--border))/0.4]
        shadow-[0_10px_40px_-10px_rgba(0,0,0,0.6)]
        transition-all duration-300
        focus-within:border-primary/50
        focus-within:shadow-[0_0_40px_-10px_hsl(var(--primary)/0.4)]
      ">

        {/* Glow Layer */}
        <div className="absolute inset-0 rounded-2xl opacity-0 focus-within:opacity-100 transition duration-300 pointer-events-none">
          <div className="absolute inset-0 rounded-2xl bg-gradient-to-r from-primary/10 via-transparent to-accent/10 blur-xl" />
        </div>

        {/* Upload */}
        <button className="relative text-muted-foreground hover:text-foreground transition-colors">
          <Upload className="h-5 w-5" />
        </button>

        {/* Input */}
        <input
          type="text"
          placeholder="Ask anything about your code..."
          className="
            flex-1 bg-transparent outline-none text-sm
            text-foreground placeholder:text-muted-foreground
          "
        />

        {/* Send Button */}
        <button
          className="
            relative w-10 h-10 rounded-xl flex items-center justify-center
            bg-gradient-to-br from-primary to-accent
            text-white
            shadow-md
            hover:scale-105
            hover:shadow-[0_0_20px_-5px_hsl(var(--primary)/0.6)]
            transition-all duration-200
          "
        >
          <SendHorizonal className="h-4 w-4" />
        </button>

      </div>
    </div>
  );
};

export default ChatInput;