import type { FeedbackResponse, HeavyEquipmentContext, MessageResponse, OBDResult, SessionMode, SessionSummary, SessionState, Vehicle } from "@/types";
import { refreshToken } from "@/lib/auth";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

async function fetchJSON<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    ...options,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API error ${res.status}: ${body}`);
  }
  return res.json() as Promise<T>;
}

async function fetchWithAuth<T>(path: string, options?: RequestInit): Promise<T> {
  try {
    return await fetchJSON<T>(path, options);
  } catch (err) {
    if (err instanceof Error && err.message.startsWith("API error 401")) {
      const refreshed = await refreshToken();
      if (refreshed) return fetchJSON<T>(path, options);
      window.location.href = "/login";
    }
    throw err;
  }
}

export async function createSession(
  description: string,
  vehicle?: Vehicle,
  options?: {
    session_mode?: SessionMode;
    heavy_context?: HeavyEquipmentContext;
  }
): Promise<MessageResponse> {
  return fetchWithAuth<MessageResponse>("/api/sessions", {
    method: "POST",
    body: JSON.stringify({
      description,
      vehicle,
      session_mode: options?.session_mode ?? "consumer",
      heavy_context: options?.heavy_context,
    }),
  });
}

export async function sendMessage(
  sessionId: string,
  content: string
): Promise<MessageResponse> {
  return fetchWithAuth<MessageResponse>(`/api/sessions/${sessionId}/message`, {
    method: "POST",
    body: JSON.stringify({ content }),
  });
}

export async function getSession(sessionId: string): Promise<SessionState> {
  return fetchWithAuth<SessionState>(`/api/sessions/${sessionId}`);
}

export async function listSessions(): Promise<SessionSummary[]> {
  return fetchWithAuth<SessionSummary[]>("/api/sessions");
}

export async function completeSession(sessionId: string): Promise<{ session_id: string; status: string }> {
  return fetchWithAuth(`/api/sessions/${sessionId}/complete`, { method: "PATCH" });
}

export async function deleteSession(sessionId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/sessions/${sessionId}`, {
    method: "DELETE",
    credentials: "include",
  });
  if (!res.ok) {
    if (res.status === 401) {
      const refreshed = await refreshToken();
      if (refreshed) {
        const retry = await fetch(`${API_BASE}/api/sessions/${sessionId}`, {
          method: "DELETE",
          credentials: "include",
        });
        if (!retry.ok) {
          const body = await retry.text();
          throw new Error(`API error ${retry.status}: ${body}`);
        }
        return;
      }
      window.location.href = "/login";
      return;
    }
    const body = await res.text();
    throw new Error(`API error ${res.status}: ${body}`);
  }
}

export async function submitFeedback(
  sessionId: string,
  rating: number,
  comment?: string
): Promise<FeedbackResponse> {
  return fetchWithAuth<FeedbackResponse>(`/api/sessions/${sessionId}/feedback`, {
    method: "POST",
    body: JSON.stringify({ rating, comment }),
  });
}

export async function lookupOBDCode(code: string, vehicle?: Vehicle): Promise<OBDResult> {
  // OBD is public — no auth needed, but include credentials anyway for consistency
  return fetchJSON<OBDResult>("/api/obd/lookup", {
    method: "POST",
    body: JSON.stringify({ code, vehicle }),
  });
}

export async function uploadImage(
  sessionId: string,
  file: File,
  confidenceModifier: number = 0.8
): Promise<MessageResponse> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("confidence_modifier", String(confidenceModifier));

  const doUpload = () =>
    fetch(`${API_BASE}/api/sessions/${sessionId}/image`, {
      method: "POST",
      body: formData,
      credentials: "include",
      // No Content-Type header — browser sets it with multipart boundary
    });

  let res = await doUpload();
  if (res.status === 401) {
    const refreshed = await refreshToken();
    if (refreshed) res = await doUpload();
    else window.location.href = "/login";
  }
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API error ${res.status}: ${body}`);
  }
  return res.json() as Promise<MessageResponse>;
}
