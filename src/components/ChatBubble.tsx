import { User, Sparkles, FileCode2, Clock } from "lucide-react";
import type { ChatMessage } from "../stores/sessionStore";

interface ChatBubbleProps {
  msg: ChatMessage;
}

/**
 * Renders a single line of inline markdown (bold, inline code, italic).
 */
function renderInline(line: string) {
  return line.split(/(`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*)/g).map((seg, si) => {
    if (seg.startsWith("`") && seg.endsWith("`")) {
      return (
        <code
          key={si}
          className="px-1.5 py-0.5 rounded text-xs font-mono text-purple-300"
          style={{ background: "hsla(228,20%,15%,0.8)" }}
        >
          {seg.slice(1, -1)}
        </code>
      );
    }
    if (seg.startsWith("**") && seg.endsWith("**")) {
      return (
        <strong key={si} className="font-semibold text-foreground">
          {seg.slice(2, -2)}
        </strong>
      );
    }
    if (seg.startsWith("*") && seg.endsWith("*") && seg.length > 2) {
      return (
        <em key={si} className="italic text-gray-300">
          {seg.slice(1, -1)}
        </em>
      );
    }
    return <span key={si}>{seg}</span>;
  });
}

/**
 * Renders markdown-like content:
 *   - Code blocks with ```
 *   - Headings (# ## ### etc.) → styled without the # symbols
 *   - Tables (| ... | rows)
 *   - Horizontal rules (--- / ***)
 *   - Unordered lists (- / *)
 *   - Ordered lists (1. 2. etc.)
 *   - Inline `code`, **bold**, *italic*
 *   - Line breaks
 */
function renderContent(text: string) {
  // 1) Split by code blocks first
  const codeBlockRegex = /```(\w*)\n?([\s\S]*?)```/g;
  const parts: Array<{ type: "text" | "code"; lang?: string; value: string }> =
    [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = codeBlockRegex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push({ type: "text", value: text.slice(lastIndex, match.index) });
    }
    parts.push({ type: "code", lang: match[1] || "text", value: match[2] });
    lastIndex = match.index + match[0].length;
  }
  if (lastIndex < text.length) {
    parts.push({ type: "text", value: text.slice(lastIndex) });
  }

  return parts.map((part, i) => {
    if (part.type === "code") {
      return (
        <div key={i} className="my-3 rounded-xl overflow-hidden">
          <div
            className="flex items-center justify-between px-4 py-2 text-xs"
            style={{
              background: "hsla(228, 20%, 8%, 0.8)",
              borderBottom: "1px solid hsla(228,15%,22%,0.3)",
            }}
          >
            <span className="text-purple-300 font-medium">{part.lang}</span>
            <button
              onClick={() => navigator.clipboard.writeText(part.value)}
              className="text-gray-500 hover:text-gray-300 transition-colors text-xs"
            >
              Copy
            </button>
          </div>
          <pre
            className="p-4 overflow-x-auto text-sm leading-relaxed"
            style={{
              background: "hsla(228, 20%, 6%, 0.9)",
              color: "#e2e8f0",
            }}
          >
            <code>{part.value}</code>
          </pre>
        </div>
      );
    }

    // 2) Process text blocks line-by-line
    const lines = part.value.split("\n");
    const elements: JSX.Element[] = [];
    let idx = 0;

    while (idx < lines.length) {
      const line = lines[idx];

      // ── Horizontal rule ────────────────────────────────
      if (/^(\s*[-*_]\s*){3,}$/.test(line.trim())) {
        elements.push(
          <div
            key={`${i}-${idx}`}
            className="my-4 h-px w-full"
            style={{
              background:
                "linear-gradient(90deg, transparent, hsla(250,80%,65%,0.3), hsla(200,80%,55%,0.3), transparent)",
            }}
          />
        );
        idx++;
        continue;
      }

      // ── Headings ───────────────────────────────────────
      const headingMatch = line.match(/^(#{1,6})\s+(.+)$/);
      if (headingMatch) {
        const level = headingMatch[1].length;
        const headingText = headingMatch[2].trim();

        const headingStyles: Record<number, string> = {
          1: "text-lg font-bold text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-blue-400 mt-4 mb-2",
          2: "text-base font-bold text-transparent bg-clip-text bg-gradient-to-r from-purple-300 to-blue-300 mt-3 mb-1.5",
          3: "text-sm font-semibold text-purple-200 mt-2 mb-1",
          4: "text-sm font-semibold text-gray-200 mt-2 mb-1",
          5: "text-xs font-semibold text-gray-300 mt-1 mb-0.5",
          6: "text-xs font-medium text-gray-400 mt-1 mb-0.5",
        };

        elements.push(
          <div key={`${i}-${idx}`} className={headingStyles[level] || headingStyles[3]}>
            {renderInline(headingText)}
          </div>
        );
        idx++;
        continue;
      }

      // ── Table block ────────────────────────────────────
      if (line.includes("|") && line.trim().startsWith("|")) {
        const tableLines: string[] = [];
        while (idx < lines.length && lines[idx].includes("|") && lines[idx].trim().startsWith("|")) {
          tableLines.push(lines[idx]);
          idx++;
        }

        // Filter out separator rows (|---|---|)
        const isSeparator = (l: string) => /^\|[\s\-:|]+\|$/.test(l.trim());
        const dataRows = tableLines.filter((l) => !isSeparator(l));

        if (dataRows.length > 0) {
          const parseRow = (row: string) =>
            row
              .split("|")
              .map((c) => c.trim())
              .filter((c) => c.length > 0);

          const headerCells = parseRow(dataRows[0]);
          const bodyRows = dataRows.slice(1).map(parseRow);

          elements.push(
            <div
              key={`${i}-table-${idx}`}
              className="my-3 rounded-xl overflow-hidden"
              style={{
                border: "1px solid hsla(228,15%,22%,0.3)",
              }}
            >
              <table className="w-full text-sm">
                <thead>
                  <tr
                    style={{
                      background: "hsla(250,80%,65%,0.1)",
                    }}
                  >
                    {headerCells.map((cell, ci) => (
                      <th
                        key={ci}
                        className="px-4 py-2.5 text-left text-xs font-semibold text-purple-300 uppercase tracking-wider"
                        style={{
                          borderBottom: "1px solid hsla(250,80%,65%,0.2)",
                        }}
                      >
                        {renderInline(cell)}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {bodyRows.map((row, ri) => (
                    <tr
                      key={ri}
                      style={{
                        background:
                          ri % 2 === 0
                            ? "hsla(228,20%,10%,0.3)"
                            : "hsla(228,20%,12%,0.3)",
                        borderBottom: "1px solid hsla(228,15%,22%,0.15)",
                      }}
                    >
                      {row.map((cell, ci) => (
                        <td
                          key={ci}
                          className="px-4 py-2.5 text-gray-300"
                        >
                          {renderInline(cell)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          );
        }
        continue;
      }

      // ── Unordered list item (- or *) ───────────────────
      const ulMatch = line.match(/^(\s*)[-*]\s+(.+)$/);
      if (ulMatch) {
        const listItems: { indent: number; content: string }[] = [];
        while (idx < lines.length) {
          const ulLine = lines[idx].match(/^(\s*)[-*]\s+(.+)$/);
          if (!ulLine) break;
          listItems.push({
            indent: ulLine[1].length,
            content: ulLine[2],
          });
          idx++;
        }

        elements.push(
          <ul key={`${i}-${idx}`} className="my-2 space-y-1.5">
            {listItems.map((item, li) => (
              <li
                key={li}
                className="flex items-start gap-2 text-gray-300"
                style={{ paddingLeft: `${item.indent + 0.5}rem` }}
              >
                <span
                  className="mt-2 shrink-0 w-1.5 h-1.5 rounded-full"
                  style={{
                    background: "linear-gradient(135deg, #a78bfa, #60a5fa)",
                  }}
                />
                <span className="leading-relaxed">{renderInline(item.content)}</span>
              </li>
            ))}
          </ul>
        );
        continue;
      }

      // ── Ordered list item (1. 2. etc.) ─────────────────
      const olMatch = line.match(/^(\s*)\d+\.\s+(.+)$/);
      if (olMatch) {
        const listItems: { content: string }[] = [];
        while (idx < lines.length) {
          const olLine = lines[idx].match(/^(\s*)\d+\.\s+(.+)$/);
          if (!olLine) break;
          listItems.push({ content: olLine[2] });
          idx++;
        }

        elements.push(
          <ol key={`${i}-${idx}`} className="my-2 space-y-1.5">
            {listItems.map((item, li) => (
              <li
                key={li}
                className="flex items-start gap-2.5 text-gray-300"
              >
                <span
                  className="shrink-0 mt-0.5 w-5 h-5 rounded-md flex items-center justify-center text-xs font-semibold text-purple-300"
                  style={{
                    background: "hsla(250,80%,65%,0.12)",
                    fontSize: "10px",
                  }}
                >
                  {li + 1}
                </span>
                <span className="leading-relaxed">{renderInline(item.content)}</span>
              </li>
            ))}
          </ol>
        );
        continue;
      }

      // ── Blank line ─────────────────────────────────────
      if (line.trim() === "") {
        elements.push(<div key={`${i}-${idx}`} className="h-2" />);
        idx++;
        continue;
      }

      // ── Regular paragraph ──────────────────────────────
      elements.push(
        <p key={`${i}-${idx}`} className="leading-relaxed">
          {renderInline(line)}
        </p>
      );
      idx++;
    }

    return <div key={i}>{elements}</div>;
  });
}

const ChatBubble = ({ msg }: ChatBubbleProps) => {
  const isUser = msg.role === "user";

  return (
    <div
      className={`flex gap-3 animate-fade-in ${
        isUser ? "justify-end" : "justify-start"
      }`}
    >
      {/* Assistant avatar */}
      {!isUser && (
        <div className="shrink-0 w-8 h-8 rounded-xl bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center mt-1">
          <Sparkles className="h-4 w-4 text-white" />
        </div>
      )}

      {/* Bubble */}
      <div
        className={`max-w-[75%] rounded-2xl px-5 py-4 ${
          isUser ? "rounded-tr-md" : "rounded-tl-md"
        }`}
        style={
          isUser
            ? {
                background:
                  "linear-gradient(135deg, hsla(250,80%,65%,0.25), hsla(200,80%,55%,0.15))",
                border: "1px solid hsla(250,80%,65%,0.2)",
              }
            : {
                background: "hsla(228, 20%, 12%, 0.5)",
                backdropFilter: "blur(20px)",
                border: "1px solid hsla(228, 15%, 22%, 0.2)",
              }
        }
      >
        {/* Content */}
        <div className="text-sm text-foreground">{renderContent(msg.content)}</div>

        {/* Meta — for assistant messages */}
        {!isUser && (
          <div className="mt-3 flex flex-wrap items-center gap-3">
            {msg.intent && (
              <span
                className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-purple-300"
                style={{
                  fontSize: "10px",
                  background: "hsla(250,80%,65%,0.12)",
                }}
              >
                <Sparkles className="h-2.5 w-2.5" />
                {msg.intent}
              </span>
            )}

            {msg.filesReferenced && msg.filesReferenced.length > 0 && (
              <span
                className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-blue-300"
                style={{
                  fontSize: "10px",
                  background: "hsla(200,80%,55%,0.12)",
                }}
              >
                <FileCode2 className="h-2.5 w-2.5" />
                {msg.filesReferenced.length} file
                {msg.filesReferenced.length > 1 ? "s" : ""}
              </span>
            )}

            {msg.timing && msg.timing.total && (
              <span
                className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-gray-400"
                style={{
                  fontSize: "10px",
                  background: "hsla(228,15%,22%,0.3)",
                }}
              >
                <Clock className="h-2.5 w-2.5" />
                {msg.timing.total.toFixed(1)}s
              </span>
            )}
          </div>
        )}
      </div>

      {/* User avatar */}
      {isUser && (
        <div
          className="shrink-0 w-8 h-8 rounded-xl flex items-center justify-center mt-1"
          style={{
            background: "hsla(228, 20%, 18%, 0.8)",
            border: "1px solid hsla(228,15%,22%,0.3)",
          }}
        >
          <User className="h-4 w-4 text-gray-400" />
        </div>
      )}
    </div>
  );
};

export default ChatBubble;