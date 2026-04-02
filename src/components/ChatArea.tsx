import { useEffect, useRef } from "react";
import { Loader2 } from "lucide-react";
import ChatBubble from "./ChatBubble";
import { useSession } from "../stores/sessionStore";

const ChatArea = () => {
  const { messages, isGenerating } = useSession();
  const bottomRef = useRef<HTMLDivElement>(null);

  console.log("[ChatArea] render, messages:", messages.length, "generating:", isGenerating);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length, isGenerating]);

  if (messages.length === 0 && !isGenerating) return null;

  return (
    <div className="flex-1 w-full max-w-3xl mx-auto overflow-y-auto px-4 py-6 space-y-6">
      {messages.map((msg) => (
        <ChatBubble key={msg.id} msg={msg} />
      ))}

      {/* Typing indicator */}
      {isGenerating && (
        <div className="flex gap-3 items-start animate-fade-in">
          <div className="shrink-0 w-8 h-8 rounded-xl bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center">
            <Loader2 className="h-4 w-4 text-white animate-spin" />
          </div>
          <div
            className="rounded-2xl rounded-tl-md px-5 py-4"
            style={{
              background: "hsla(228, 20%, 12%, 0.5)",
              border: "1px solid hsla(228, 15%, 22%, 0.2)",
            }}
          >
            <div className="flex items-center gap-1.5">
              <div
                className="w-2 h-2 rounded-full bg-purple-400"
                style={{ animation: "pulse-slow 1.4s ease-in-out infinite" }}
              />
              <div
                className="w-2 h-2 rounded-full bg-purple-400"
                style={{
                  animation: "pulse-slow 1.4s ease-in-out infinite",
                  animationDelay: "0.2s",
                }}
              />
              <div
                className="w-2 h-2 rounded-full bg-purple-400"
                style={{
                  animation: "pulse-slow 1.4s ease-in-out infinite",
                  animationDelay: "0.4s",
                }}
              />
            </div>
          </div>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
};

export default ChatArea;