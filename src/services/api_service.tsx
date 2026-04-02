const API_BASE = "http://127.0.0.1:8000/api";

export interface UploadResponse {
  session_id: string;
  status: string;
  message: string;
}

export interface StatusResponse {
  session_id: string;
  status: "analyzing" | "ready" | "error";
  message: string;
  repo_summary: {
    total_pages: number;
    languages: string[];
    files: string[];
  } | null;
}

export async function uploadRepoUrl(repoUrl: string): Promise<UploadResponse> {
  const res = await fetch(`${API_BASE}/upload/url`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ repo_url: repoUrl }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Upload failed" }));
    throw new Error(err.detail || "Upload failed");
  }
  return res.json();
}

export async function checkStatus(sessionId: string): Promise<StatusResponse> {
  const res = await fetch(`${API_BASE}/status/${sessionId}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Status check failed" }));
    throw new Error(err.detail || "Status check failed");
  }
  return res.json();
}