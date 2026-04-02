import type { ChatResult } from "../services/api_service";

/**
 * Extracts human-readable content from the ChatResponse.result object.
 * Matches the backend's result types: explanation, modification, debugging, testing, error.
 */
export function extractContent(
  result: ChatResult,
  planSummary?: string
): string {
  if (!result) {
    return planSummary || "No response generated.";
  }

  const resultType = result.type || "";

  // ── explanation ────────────────────────────────────────────────
  if (resultType === "explanation") {
    return result.content || planSummary || "No explanation available.";
  }

  // ── modification ───────────────────────────────────────────────
  if (resultType === "modification") {
    const parts: string[] = [];
    if (result.summary) {
      parts.push(result.summary);
    }
    const changes = result.changes || [];
    if (changes.length > 0) {
      parts.push(`\n**${changes.length} file(s) modified:**\n`);
      for (const change of changes) {
        parts.push(`### \`${change.file_path}\``);
        if (change.diff) {
          parts.push("```diff\n" + change.diff + "\n```");
        } else if (change.modified) {
          const ext = change.file_path.split(".").pop() || "text";
          parts.push("```" + ext + "\n" + change.modified + "\n```");
        }
      }
    }
    return parts.join("\n") || planSummary || "Code modification completed.";
  }

  // ── debugging ──────────────────────────────────────────────────
  if (resultType === "debugging") {
    const parts: string[] = [];
    const debug = result.debug;
    if (debug) {
      if (debug.overall_assessment) {
        parts.push(debug.overall_assessment);
      }
      const bugs = debug.bugs || [];
      if (bugs.length > 0) {
        parts.push(`\n**Found ${bugs.length} issue(s):**\n`);
        bugs.forEach((bug, i) => {
          parts.push(
            `${i + 1}. ${bug.severity ? `**[${bug.severity}]** ` : ""}${bug.description}`
          );
          if (bug.fix) {
            parts.push(`   → **Fix:** ${bug.fix}`);
          }
        });
      }
    }
    return parts.join("\n") || planSummary || "Debug analysis complete.";
  }

  // ── testing ────────────────────────────────────────────────────
  if (resultType === "testing") {
    const parts: string[] = [];
    if (result.summary) {
      parts.push(result.summary);
    }
    const testFiles = result.test_files || [];
    if (testFiles.length > 0) {
      parts.push(`\n**Generated ${testFiles.length} test file(s):**\n`);
      for (const tf of testFiles) {
        const ext = tf.file_path.split(".").pop() || "text";
        parts.push(`### \`${tf.file_path}\``);
        parts.push("```" + ext + "\n" + tf.content + "\n```");
      }
    }
    return parts.join("\n") || planSummary || "Tests generated.";
  }

  // ── error ──────────────────────────────────────────────────────
  if (resultType === "error") {
    return `⚠️ ${result.content || "An error occurred."}`;
  }

  // ── fallback: content field or stringify ────────────────────────
  if (result.content && typeof result.content === "string") {
    return result.content;
  }

  if (planSummary) {
    return planSummary;
  }

  // Last resort — pretty print the result
  return "```json\n" + JSON.stringify(result, null, 2) + "\n```";
}