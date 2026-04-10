"use client";

import type { ChatMessage } from "@/types";
import { DiagnosticResultCard, OBDResultCard } from "./DiagnosticResult";

function renderMarkdown(text: string): string {
  // Minimal markdown: bold, line breaks
  return text
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/\n/g, "<br />");
}

export function MessageBubble({
  message,
  sessionId,
}: {
  message: ChatMessage;
  sessionId?: string;
}) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div className={`max-w-[85%] ${isUser ? "order-2" : "order-1"}`}>
        {/* Avatar */}
        <div className={`flex items-end gap-2 ${isUser ? "flex-row-reverse" : "flex-row"}`}>
          <div
            className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 mb-1 ${
              isUser
                ? "bg-slate-800 text-white"
                : "bg-gradient-to-br from-cyan-500 to-cyan-700 text-white"
            }`}
          >
            {isUser ? "U" : "AI"}
          </div>

          <div className="flex-1">
            {message.obd_result ? (
              <OBDResultCard result={message.obd_result} />
            ) : message.result ? (
              <DiagnosticResultCard result={message.result} sessionId={sessionId} />
            ) : message.msg_type === "image" ? (
              /* Uploaded photo thumbnail */
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={message.content}
                alt="Uploaded photo"
                className="h-40 max-w-xs object-cover rounded-2xl rounded-br-sm border border-gray-100 shadow-card"
              />
            ) : (
              <div
                className={`px-4 py-3 rounded-2xl text-sm leading-relaxed ${
                  isUser
                    ? "bg-cyan-600 text-white rounded-br-sm"
                    : "bg-white border border-gray-100 text-slate-800 rounded-bl-sm shadow-card"
                }`}
              >
                <p
                  dangerouslySetInnerHTML={{ __html: renderMarkdown(message.content) }}
                />
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
