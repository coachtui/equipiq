"use client";

import { useState, useEffect, useRef } from "react";
import { completeSession, createSession, deleteSession, getSession, listSessions, lookupOBDCode, sendMessage, uploadImage } from "@/lib/api";
import type { ChatMessage, HeavyEquipmentContext, OBDResult, SessionMode, SessionSummary } from "@/types";
import { HeavyEquipmentForm } from "./HeavyEquipmentForm";
import { MessageBubble } from "./MessageBubble";
import { useAuth } from "@/context/AuthContext";

const WELCOME = "Describe your engine or vehicle problem and I'll help narrow down the likely cause. Include your vehicle year, make, and model if you know it.";

type Phase = "idle" | "active" | "awaiting_followup";

const SYMPTOM_LABELS: Record<string, string> = {
  no_crank: "No Crank",
  crank_no_start: "Crank No Start",
  loss_of_power: "Loss of Power",
  rough_idle: "Rough Idle",
  strange_noise: "Strange Noise",
  visible_leak: "Visible Leak",
  overheating: "Overheating",
  check_engine_light: "Check Engine Light",
  brakes: "Brakes",
  transmission: "Transmission",
  suspension: "Suspension",
  hvac: "HVAC",
  no_crank_motorcycle: "No Crank (Motorcycle)",
  crank_no_start_motorcycle: "Crank No Start (Motorcycle)",
  rough_idle_motorcycle: "Rough Idle (Motorcycle)",
  loss_of_power_motorcycle: "Loss of Power (Motorcycle)",
  strange_noise_motorcycle: "Strange Noise (Motorcycle)",
  visible_leak_motorcycle: "Visible Leak (Motorcycle)",
};

const DTC_RE = /^[PBCUpbcu]\d{4}$/;

function SessionHistoryItem({
  session,
  onResume,
  onDelete,
}: {
  session: SessionSummary;
  onResume: (id: string) => void;
  onDelete: (id: string) => void;
}) {
  const [confirmDelete, setConfirmDelete] = useState(false);

  const vehicle = [session.vehicle_year, session.vehicle_make, session.vehicle_model]
    .filter(Boolean)
    .join(" ");
  const symptom = session.symptom_category
    ? (SYMPTOM_LABELS[session.symptom_category] ?? session.symptom_category)
    : "Unknown";
  const date = new Date(session.created_at).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
  const isOpen = session.status === "active" || session.status === "awaiting_followup";
  const isResolved = session.status === "complete";

  return (
    <div className="relative group w-full">
      <button
        onClick={() => !confirmDelete && onResume(session.session_id)}
        className="w-full text-left px-3 py-2.5 rounded-xl hover:bg-cyan-50 transition-colors pr-8 cursor-pointer"
      >
        <div className="flex items-start justify-between gap-2">
          <span className="text-xs font-medium text-slate-800 truncate">
            {vehicle || "Unknown vehicle"}
          </span>
          <span className="text-xs text-slate-400 flex-shrink-0">{date}</span>
        </div>
        <div className="flex items-center gap-1.5 mt-0.5 flex-wrap">
          <span className="text-xs text-slate-500">{symptom}</span>
          {session.vehicle_type && session.vehicle_type !== "car" && session.vehicle_type !== "truck" && (
            <span className="text-xs text-cyan-600 capitalize">· {session.vehicle_type}</span>
          )}
          {isOpen && <span className="text-xs text-cyan-600 font-medium">· Open</span>}
          {isResolved && <span className="text-xs text-green-600 font-medium">· Resolved</span>}
        </div>
        {session.top_cause && (
          <p className="text-xs text-slate-500 truncate mt-0.5 font-medium">{session.top_cause}</p>
        )}
        <p className="text-xs text-slate-400 truncate mt-0.5">{session.excerpt}</p>
      </button>

      {/* Delete controls — appear on hover */}
      <div className="absolute top-2 right-2">
        {!confirmDelete ? (
          <button
            onClick={(e) => { e.stopPropagation(); setConfirmDelete(true); }}
            className="opacity-0 group-hover:opacity-100 transition text-slate-300 hover:text-red-500 p-0.5 cursor-pointer"
            aria-label="Delete session"
          >
            <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round"
                d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
            </svg>
          </button>
        ) : (
          <div className="flex items-center gap-1 text-xs bg-white border border-gray-100 rounded-lg px-1.5 py-0.5 shadow-card">
            <button
              onClick={(e) => { e.stopPropagation(); onDelete(session.session_id); }}
              className="text-red-600 hover:text-red-800 font-medium cursor-pointer"
            >
              Del
            </button>
            <span className="text-gray-200">|</span>
            <button
              onClick={(e) => { e.stopPropagation(); setConfirmDelete(false); }}
              className="text-slate-400 hover:text-slate-700 cursor-pointer"
            >
              Cancel
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export function ChatInterface() {
  const { user, logout } = useAuth();
  const [phase, setPhase] = useState<Phase>("idle");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<SessionSummary[]>([]);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [pendingFile, setPendingFile] = useState<File | null>(null);
  const [confidenceModifier, setConfidenceModifier] = useState<number>(0.8);
  const [showHistorySheet, setShowHistorySheet] = useState(false);
  const [showOBDModal, setShowOBDModal] = useState(false);
  const [resolvedSessionIds, setResolvedSessionIds] = useState<Set<string>>(new Set());
  const [sessionMode, setSessionMode] = useState<SessionMode>("consumer");
  const [showHeavyForm, setShowHeavyForm] = useState(false);
  const [heavyContext, setHeavyContext] = useState<HeavyEquipmentContext>({});
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  useEffect(() => {
    if (!loading) inputRef.current?.focus();
  }, [loading, phase]);

  useEffect(() => {
    listSessions().then(setHistory).catch(() => {});
  }, []);

  const refreshHistory = () => {
    listSessions().then(setHistory).catch(() => {});
  };

  const pushMessage = (msg: ChatMessage) =>
    setMessages((prev) => [...prev, msg]);

  async function handleResume(id: string) {
    setLoading(true);
    setError(null);
    try {
      const state = await getSession(id);
      const restored: ChatMessage[] = state.messages.map((m) => ({
        role: m.role as "user" | "assistant",
        content: m.content,
        msg_type: m.type as ChatMessage["msg_type"],
        result: m.type === "result" && state.result ? state.result : undefined,
      }));
      setMessages(restored);
      setSessionId(id);
      setPhase(
        state.status === "awaiting_followup"
          ? "awaiting_followup"
          : state.status === "active"
          ? "active"
          : "awaiting_followup"
      );
    } catch {
      setError("Couldn't load that session.");
    } finally {
      setLoading(false);
    }
  }

  async function handleDelete(id: string) {
    try {
      await deleteSession(id);
      setHistory((prev) => prev.filter((s) => s.session_id !== id));
      if (sessionId === id) handleNewSession();
    } catch {
      setError("Could not delete session.");
    }
  }

  async function handleMarkResolved() {
    if (!sessionId) return;
    try {
      await completeSession(sessionId);
      setResolvedSessionIds((prev) => new Set([...prev, sessionId]));
      refreshHistory();
    } catch {
      setError("Could not mark session as resolved.");
    }
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setPendingFile(file);
    if (file.type.startsWith("video/")) {
      setImagePreview("__video__");
    } else {
      const reader = new FileReader();
      reader.onload = (ev) => setImagePreview(ev.target?.result as string);
      reader.readAsDataURL(file);
    }
    e.target.value = "";
  }

  function clearImage() {
    setPendingFile(null);
    setImagePreview(null);
  }

  async function handleSend() {
    const text = input.trim();
    if (!text && !pendingFile) return;
    if (loading) return;
    setInput("");
    setError(null);
    setLoading(true);

    if (pendingFile) {
      const file = pendingFile;
      const preview = imagePreview;
      clearImage();

      if (!sessionId && phase === "idle") {
        const desc = text || "I'm uploading a photo of my engine issue.";
        if (!text) pushMessage({ role: "user", content: desc });
        try {
          const res = await createSession(desc, undefined, {
            session_mode: sessionMode,
            heavy_context: showHeavyForm ? heavyContext : undefined,
          });
          if (res.session_id) {
            setSessionId(res.session_id);
            pushMessage({ role: "assistant", content: res.message, msg_type: res.msg_type, result: res.result ?? undefined });
            if (res.msg_type === "result") setPhase("awaiting_followup");
            else setPhase("active");
            refreshHistory();
            await _uploadImageToSession(res.session_id, file, preview);
          }
        } catch (err) {
          const msg = err instanceof Error ? err.message : "Something went wrong.";
          setError(msg);
        } finally {
          setLoading(false);
        }
        return;
      }

      if (sessionId) {
        if (text) pushMessage({ role: "user", content: text });
        pushMessage({ role: "user", content: preview ?? "[Photo]", msg_type: "image" as ChatMessage["msg_type"] });
        try {
          await _uploadImageToSession(sessionId, file, preview);
          if (text) {
            const res = await sendMessage(sessionId, text);
            pushMessage({ role: "assistant", content: res.message, msg_type: res.msg_type, result: res.result ?? undefined });
            if (res.msg_type === "result") setPhase("awaiting_followup");
            refreshHistory();
          }
        } catch (err) {
          const msg = err instanceof Error ? err.message : "Something went wrong.";
          setError(msg);
        } finally {
          setLoading(false);
        }
        return;
      }
    }

    pushMessage({ role: "user", content: text });

    try {
      if (phase === "idle" && DTC_RE.test(text.trim())) {
        // Auto-detect DTC code — skip tree traversal entirely
        try {
          const result = await lookupOBDCode(text.trim().toUpperCase());
          pushMessage({ role: "assistant", content: "", msg_type: "result", obd_result: result });
        } catch {
          setError("OBD code lookup failed. Try again.");
        }
        setLoading(false);
        return;
      }

      if (phase === "idle") {
        const res = await createSession(text, undefined, {
          session_mode: sessionMode,
          heavy_context: showHeavyForm ? heavyContext : undefined,
        });
        if (res.session_id) setSessionId(res.session_id);

        pushMessage({
          role: "assistant",
          content: res.message,
          msg_type: res.msg_type,
          result: res.result ?? undefined,
        });

        if (res.msg_type === "result") {
          setPhase("awaiting_followup");
        } else if (res.msg_type !== "error") {
          setPhase("active");
        }
        refreshHistory();
      } else {
        if (!sessionId) return;
        const res = await sendMessage(sessionId, text);

        if (res.msg_type === "result" && res.result) {
          const isFollowup = phase === "awaiting_followup";
          if (isFollowup) {
            pushMessage({ role: "assistant", content: res.message, msg_type: "chat" });
          }
          pushMessage({
            role: "assistant",
            content: "",
            msg_type: "result",
            result: res.result,
          });
          setPhase("awaiting_followup");
        } else {
          pushMessage({
            role: "assistant",
            content: res.message,
            msg_type: res.msg_type,
          });
          if (res.msg_type === "result") setPhase("awaiting_followup");
        }
        refreshHistory();
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Something went wrong.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  async function _uploadImageToSession(sid: string, file: File, preview: string | null) {
    try {
      const res = await uploadImage(sid, file, confidenceModifier);
      pushMessage({ role: "assistant", content: res.message, msg_type: "chat" });
      refreshHistory();
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Image upload failed.";
      setError(msg);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  function handleNewSession() {
    setPhase("idle");
    setMessages([]);
    setSessionId(null);
    setInput("");
    setError(null);
  }

  const inputPlaceholder =
    phase === "idle"
      ? "Describe your engine problem (e.g. '2018 Honda Civic won't start, no clicking sound')…"
      : phase === "awaiting_followup"
      ? "Report what you found from those checks…"
      : "Type your answer…";

  const showHistory = phase === "idle" && history.length > 0;
  const isResolved = sessionId ? resolvedSessionIds.has(sessionId) : false;

  return (
    <div className="flex h-full">
      {/* Session history sidebar — hidden on mobile */}
      {showHistory && (
        <div className="hidden sm:flex w-60 flex-shrink-0 border-r border-gray-100 bg-white/80 flex-col">
          <div className="px-3 py-3 border-b border-gray-100">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Recent Sessions
            </p>
          </div>
          <div className="flex-1 overflow-y-auto py-2 px-2 space-y-0.5 scrollbar-thin">
            {history.map((s) => (
              <SessionHistoryItem
                key={s.session_id}
                session={s}
                onResume={handleResume}
                onDelete={handleDelete}
              />
            ))}
          </div>
        </div>
      )}

      {/* Main chat area */}
      <div className="flex flex-col flex-1 max-w-2xl mx-auto">
        {/* Header */}
        <div className="flex-shrink-0 px-4 py-4 border-b border-gray-100 bg-white shadow-[0_1px_0_rgba(0,0,0,0.04)] flex items-center justify-between">
          <div>
            <h1 className="text-lg font-bold text-slate-900 tracking-tight">Fix</h1>
            <p className="text-xs text-slate-400">AI Engine &amp; Drivetrain Diagnostic</p>
          </div>
          <div className="flex items-center gap-2">
            {history.length > 0 && (
              <button
                onClick={() => setShowHistorySheet(true)}
                className="sm:hidden flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-800 border border-gray-200 rounded-xl px-3 py-1.5 transition-colors cursor-pointer"
              >
                <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                History
              </button>
            )}
            {phase !== "idle" && (
              <button
                onClick={handleNewSession}
                className="text-xs text-slate-500 hover:text-slate-800 border border-gray-200 rounded-xl px-3 py-1.5 transition-colors cursor-pointer"
              >
                New Session
              </button>
            )}
            {user && (
              <div className="flex items-center gap-2 pl-2 border-l border-gray-100">
                <span className="text-xs text-slate-400 hidden sm:block truncate max-w-[140px]">{user.email}</span>
                {user.is_admin && (
                  <a
                    href="/admin"
                    className="text-xs text-slate-500 hover:text-cyan-600 border border-gray-200 rounded-xl px-3 py-1.5 transition-colors"
                  >
                    Admin
                  </a>
                )}
                {(user.is_operator || user.is_admin) && (
                  <a
                    href="/fleet"
                    className="text-xs text-slate-500 hover:text-cyan-600 border border-gray-200 rounded-xl px-3 py-1.5 transition-colors"
                  >
                    Fleet
                  </a>
                )}
                <button
                  onClick={logout}
                  className="text-xs text-slate-500 hover:text-slate-800 border border-gray-200 rounded-xl px-3 py-1.5 transition-colors cursor-pointer"
                >
                  Sign out
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4 scrollbar-thin">
          {messages.length === 0 && (
            <>
              <div className="flex justify-start">
                <div className="flex items-end gap-2">
                  <div className="w-7 h-7 rounded-full bg-gradient-to-br from-cyan-500 to-cyan-700 text-white flex items-center justify-center text-xs font-bold mb-1 flex-shrink-0">
                    AI
                  </div>
                  <div className="bg-white border border-gray-100 shadow-card rounded-2xl rounded-bl-sm px-4 py-3 max-w-md">
                    <p className="text-sm text-slate-700 leading-relaxed">{WELCOME}</p>
                  </div>
                </div>
              </div>
              <div className="flex justify-start ml-9">
                <button
                  onClick={() => setShowOBDModal(true)}
                  className="text-xs text-cyan-700 bg-cyan-50 border border-cyan-100 rounded-full px-3 py-1.5 hover:bg-cyan-100 transition-colors cursor-pointer"
                >
                  I have a DTC / OBD code →
                </button>
              </div>

              {/* Session mode selector */}
              <div className="flex justify-start ml-9">
                <div className="flex items-center gap-1 text-xs text-slate-500">
                  <span className="mr-1 text-slate-400">Mode:</span>
                  {(["consumer", "operator", "mechanic"] as const).map((mode) => (
                    <button
                      key={mode}
                      onClick={() => setSessionMode(mode)}
                      className={`px-2.5 py-1 rounded-full border transition-all capitalize cursor-pointer ${
                        sessionMode === mode
                          ? "bg-cyan-600 border-cyan-600 text-white"
                          : "border-gray-200 text-slate-500 hover:border-cyan-300 hover:text-cyan-700"
                      }`}
                    >
                      {mode}
                    </button>
                  ))}
                </div>
              </div>

              {/* Heavy equipment context toggle + form */}
              <div className="flex justify-start ml-9 flex-col gap-2">
                <button
                  onClick={() => setShowHeavyForm((v) => !v)}
                  className="text-xs text-amber-700 bg-amber-50/80 border border-amber-200/80 rounded-full px-3 py-1.5 hover:bg-amber-100 transition-colors w-fit cursor-pointer"
                >
                  {showHeavyForm ? "Hide heavy equipment details ↑" : "Heavy equipment? Add context →"}
                </button>
                {showHeavyForm && (
                  <HeavyEquipmentForm value={heavyContext} onChange={setHeavyContext} />
                )}
              </div>
            </>
          )}

          {messages.map((msg, i) => (
            <MessageBubble key={i} message={msg} sessionId={sessionId ?? undefined} />
          ))}

          {/* Follow-up prompt + resolved button after diagnosis */}
          {phase === "awaiting_followup" && !loading && (
            <div className="flex justify-start">
              <div className="flex items-end gap-2">
                <div className="w-7 h-7 rounded-full bg-gradient-to-br from-cyan-500 to-cyan-700 text-white flex items-center justify-center text-xs font-bold mb-1 flex-shrink-0">
                  AI
                </div>
                <div>
                  <div className="bg-cyan-50 border border-cyan-100 rounded-2xl rounded-bl-sm px-4 py-3 max-w-md">
                    <p className="text-sm text-cyan-900 leading-relaxed">
                      Go through those checks and come back — tell me what you find and I&apos;ll refine the diagnosis.
                    </p>
                  </div>
                  {!isResolved && sessionId && (
                    <div className="mt-1.5 ml-0.5">
                      <button
                        onClick={handleMarkResolved}
                        className="text-xs text-green-700 bg-green-50 border border-green-200 rounded-xl px-3 py-1.5 hover:bg-green-100 transition-colors cursor-pointer"
                      >
                        Mark as resolved
                      </button>
                    </div>
                  )}
                  {isResolved && (
                    <p className="text-xs text-green-600 mt-1.5 ml-0.5 font-medium">Marked as resolved</p>
                  )}
                </div>
              </div>
            </div>
          )}

          {loading && (
            <div className="flex justify-start">
              <div className="flex items-end gap-2">
                <div className="w-7 h-7 rounded-full bg-gradient-to-br from-cyan-500 to-cyan-700 text-white flex items-center justify-center text-xs font-bold mb-1 flex-shrink-0">
                  AI
                </div>
                <div className="bg-white border border-gray-100 shadow-card rounded-2xl rounded-bl-sm px-4 py-3">
                  <div className="flex gap-1 items-center h-4">
                    <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-bounce" style={{ animationDelay: "0ms" }} />
                    <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-bounce" style={{ animationDelay: "150ms" }} />
                    <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-bounce" style={{ animationDelay: "300ms" }} />
                  </div>
                </div>
              </div>
            </div>
          )}

          {error && (
            <div className="text-center">
              <span className="text-xs text-red-600 bg-red-50 border border-red-100 rounded-xl px-3 py-1.5 inline-block">
                {error}
              </span>
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <div
          className="flex-shrink-0 px-4 py-3 border-t border-gray-100 bg-white shadow-[0_-1px_4px_rgba(0,0,0,0.04)]"
          style={{ paddingBottom: "max(0.75rem, env(safe-area-inset-bottom))" }}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*,video/*"
            capture="environment"
            className="hidden"
            onChange={handleFileChange}
          />

          {imagePreview && (
            <div className="mb-2">
              <div className="relative inline-block">
                {imagePreview === "__video__" ? (
                  <div className="h-20 w-20 rounded-xl border border-gray-100 bg-slate-50 flex flex-col items-center justify-center text-slate-400 text-xs gap-1">
                    <svg className="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 10.5l4.72-4.72a.75.75 0 011.28.53v11.38a.75.75 0 01-1.28.53l-4.72-4.72M4.5 18.75h9a2.25 2.25 0 002.25-2.25v-9a2.25 2.25 0 00-2.25-2.25h-9A2.25 2.25 0 002.25 7.5v9a2.25 2.25 0 002.25 2.25z" />
                    </svg>
                    Video
                  </div>
                ) : (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={imagePreview}
                    alt="Preview"
                    className="h-20 w-20 object-cover rounded-xl border border-gray-100"
                  />
                )}
                <button
                  onClick={clearImage}
                  className="absolute -top-1.5 -right-1.5 w-5 h-5 rounded-full bg-slate-700 text-white flex items-center justify-center text-xs leading-none cursor-pointer"
                  aria-label="Remove file"
                >
                  ×
                </button>
              </div>
              <div className="mt-2 flex items-center gap-2">
                <label className="text-xs text-slate-500 flex-shrink-0">Vision trust:</label>
                <input
                  type="range"
                  min={0}
                  max={1}
                  step={0.05}
                  value={confidenceModifier}
                  onChange={(e) => setConfidenceModifier(parseFloat(e.target.value))}
                  className="flex-1 accent-cyan-600"
                />
                <span className="text-xs text-slate-600 w-8 text-right flex-shrink-0 tabular-nums">
                  {Math.round(confidenceModifier * 100)}%
                </span>
              </div>
            </div>
          )}

          {/* "Not sure" quick reply — shown only during active diagnostic questioning */}
          {phase === "active" && !loading && (
            <div className="mb-2 flex gap-2">
              <button
                onClick={() => setInput("Not sure")}
                className="text-xs text-slate-500 border border-gray-200 rounded-full px-3 py-1.5 hover:bg-cyan-50 hover:border-cyan-300 hover:text-cyan-700 transition-all min-h-[44px] cursor-pointer"
              >
                Not sure
              </button>
              <button
                onClick={() => setInput("I don't know")}
                className="text-xs text-slate-500 border border-gray-200 rounded-full px-3 py-1.5 hover:bg-cyan-50 hover:border-cyan-300 hover:text-cyan-700 transition-all min-h-[44px] cursor-pointer"
              >
                I don&apos;t know
              </button>
            </div>
          )}

          <div className="flex gap-2 items-end">
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={loading}
              className="flex-shrink-0 w-10 h-10 rounded-xl border border-gray-200 text-slate-400 flex items-center justify-center hover:bg-cyan-50 hover:border-cyan-200 hover:text-cyan-600 disabled:opacity-40 disabled:cursor-not-allowed transition-all cursor-pointer"
              aria-label="Attach photo"
            >
              <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6.827 6.175A2.31 2.31 0 015.186 7.23c-.38.054-.757.112-1.134.175C2.999 7.58 2.25 8.507 2.25 9.574V18a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9.574c0-1.067-.75-1.994-1.802-2.169a47.865 47.865 0 00-1.134-.175 2.31 2.31 0 01-1.64-1.055l-.822-1.316a2.192 2.192 0 00-1.736-1.039 48.774 48.774 0 00-5.232 0 2.192 2.192 0 00-1.736 1.039l-.821 1.316z" />
                <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 12.75a4.5 4.5 0 11-9 0 4.5 4.5 0 019 0zM18.75 10.5h.008v.008h-.008V10.5z" />
              </svg>
            </button>

            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={loading}
              placeholder={imagePreview ? "Add a caption (optional)…" : inputPlaceholder}
              rows={2}
              className="flex-1 resize-none rounded-xl border border-gray-200 bg-gray-50/30 px-3 py-2.5 text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent disabled:bg-gray-50 disabled:text-slate-400 transition-all"
            />
            <button
              onClick={handleSend}
              disabled={loading || (!input.trim() && !pendingFile)}
              className="flex-shrink-0 w-10 h-10 rounded-xl bg-cyan-600 text-white flex items-center justify-center hover:bg-cyan-700 active:scale-[0.95] disabled:opacity-40 disabled:cursor-not-allowed transition-all cursor-pointer"
              aria-label="Send"
            >
              <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
              </svg>
            </button>
          </div>
          <p className="text-xs text-slate-400 mt-1.5 ml-1">
            {phase === "awaiting_followup"
              ? "Take your time — come back when you've checked"
              : "Press Enter to send · Shift+Enter for new line"}
          </p>
        </div>
      </div>

      {/* OBD code lookup modal */}
      {showOBDModal && (
        <OBDModal
          onClose={() => setShowOBDModal(false)}
          onResult={(result) => {
            pushMessage({ role: "assistant", content: "", msg_type: "result", obd_result: result });
          }}
        />
      )}

      {/* Mobile history bottom sheet */}
      {showHistorySheet && (
        <div className="fixed inset-0 z-50 sm:hidden flex flex-col justify-end">
          <div
            className="absolute inset-0 bg-black/40 backdrop-blur-sm"
            onClick={() => setShowHistorySheet(false)}
          />
          <div className="relative bg-white rounded-t-2xl max-h-[70vh] flex flex-col">
            <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
              <p className="text-sm font-semibold text-slate-800">Recent Sessions</p>
              <button
                onClick={() => setShowHistorySheet(false)}
                className="text-slate-400 hover:text-slate-700 text-xl leading-none cursor-pointer"
                aria-label="Close"
              >
                ×
              </button>
            </div>
            <div className="overflow-y-auto py-2 px-2 space-y-0.5 scrollbar-thin">
              {history.map((s) => (
                <SessionHistoryItem
                  key={s.session_id}
                  session={s}
                  onResume={(id) => {
                    setShowHistorySheet(false);
                    handleResume(id);
                  }}
                  onDelete={handleDelete}
                />
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function OBDModal({
  onClose,
  onResult,
}: {
  onClose: () => void;
  onResult: (result: OBDResult) => void;
}) {
  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleLookup() {
    const trimmed = code.trim().toUpperCase();
    if (!DTC_RE.test(trimmed)) {
      setError("Enter a valid DTC code (e.g. P0420, B1234, C0035, U0100)");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const result = await lookupOBDCode(trimmed);
      onResult(result);
      onClose();
    } catch {
      setError("Lookup failed. Check the code and try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-sm mx-4 p-6">
        <h2 className="text-base font-semibold text-slate-900 mb-1">OBD / DTC Code Lookup</h2>
        <p className="text-xs text-slate-500 mb-4">Enter the fault code from your scan tool or dashboard.</p>
        <input
          autoFocus
          value={code}
          onChange={(e) => setCode(e.target.value.toUpperCase())}
          onKeyDown={(e) => e.key === "Enter" && handleLookup()}
          placeholder="e.g. P0420"
          className="w-full border border-gray-200 bg-gray-50/50 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent mb-3 font-mono tracking-widest transition"
          maxLength={5}
        />
        {error && <p className="text-xs text-red-600 mb-3">{error}</p>}
        <div className="flex gap-2">
          <button
            onClick={handleLookup}
            disabled={loading}
            className="flex-1 bg-cyan-600 text-white text-sm rounded-xl py-2.5 hover:bg-cyan-700 active:scale-[0.98] disabled:opacity-40 transition-all cursor-pointer"
          >
            {loading ? "Looking up…" : "Look up code"}
          </button>
          <button
            onClick={onClose}
            className="px-4 text-sm text-slate-500 hover:text-slate-800 border border-gray-200 rounded-xl transition-colors cursor-pointer"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
