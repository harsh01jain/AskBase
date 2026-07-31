/* eslint-disable @typescript-eslint/no-unused-vars, @typescript-eslint/no-explicit-any, react/no-unescaped-entities */
"use client";

import { useState, useEffect, useRef } from "react";
import { useTheme } from "next-themes";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip as RechartsTooltip, ResponsiveContainer, Cell,
} from "recharts";

/* ── Icons (inline SVGs to avoid bloat) ── */
const IconSend = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 2 11 13"/><path d="M22 2 15 22 11 13 2 9z"/></svg>
);
const IconMic = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" x2="12" y1="19" y2="22"/></svg>
);
const IconPlus = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14"/><path d="M12 5v14"/></svg>
);
const IconHistory = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M12 7v5l4 2"/></svg>
);
const IconDatabase = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14c0 1.66 4.03 3 9 3s9-1.34 9-3V5"/><path d="M3 12c0 1.66 4.03 3 9 3s9-1.34 9-3"/></svg>
);
const IconTable = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 3v18"/><rect width="18" height="18" x="3" y="3" rx="2"/><path d="M3 9h18"/><path d="M3 15h18"/></svg>
);
const IconChart = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" x2="18" y1="20" y2="10"/><line x1="12" x2="12" y1="20" y2="4"/><line x1="6" x2="6" y1="20" y2="14"/></svg>
);
const IconX = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
);
const IconChevron = ({ open }: { open: boolean }) => (
  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={`transition-transform duration-200 ${open ? 'rotate-90' : ''}`}><path d="m9 18 6-6-6-6"/></svg>
);
const IconCode = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>
);
const IconCopy = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect width="14" height="14" x="8" y="8" rx="2" ry="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/></svg>
);
const IconCheck = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M20 6 9 17l-5-5"/></svg>
);
const IconSun = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/><path d="m4.93 4.93 1.41 1.41"/><path d="m17.66 17.66 1.41 1.41"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="m6.34 17.66-1.41 1.41"/><path d="m19.07 4.93-1.41 1.41"/></svg>
);
const IconMoon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/></svg>
);

const CHART_COLORS = ["#7c9cff", "#f59e0b", "#10b981", "#f472b6", "#8b5cf6", "#06b6d4"];

export default function Home() {
  const { theme, setTheme } = useTheme();
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [schema, setSchema] = useState<any[]>([]);
  const [mounted, setMounted] = useState(false);
  const [copiedSql, setCopiedSql] = useState(false);

  // Conversation state
  const [messages, setMessages] = useState<any[]>([]);
  const [chatHistory, setChatHistory] = useState<{question: string, sql: string}[]>([]);
  const [suggestions, setSuggestions] = useState<string[]>([
    "How many total products are there?",
    "What is the average order amount?",
    "Show me the top 5 customers by revenue",
  ]);

  // Sidebar
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [schemaExpanded, setSchemaExpanded] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [history, setHistory] = useState<any[]>([]);
  const [expandedTable, setExpandedTable] = useState<number | null>(null);

  // Results view
  const [activeTab, setActiveTab] = useState<"table" | "chart">("table");

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => setMounted(true), []);

  useEffect(() => {
    fetch("http://localhost:8000/schema")
      .then((res) => res.json())
      .then((data) => setSchema(data))
      .catch(() => {});
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const loadHistory = () => {
    fetch("http://localhost:8000/history")
      .then((res) => res.ok ? res.json() : [])
      .then((data) => { setHistory(Array.isArray(data) ? data : []); setHistoryOpen(true); })
      .catch(() => { setHistory([]); setHistoryOpen(true); });
  };

  const toggleListening = () => {
    if (isListening) { setIsListening(false); return; }
    const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SR) { alert("Speech Recognition not supported."); return; }
    const recognition = new SR();
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = "en-US";
    recognition.onstart = () => setIsListening(true);
    recognition.onresult = (event: any) => {
      const transcript = Array.from(event.results).map((r: any) => r[0].transcript).join("");
      setQuestion(transcript);
    };
    recognition.onerror = () => setIsListening(false);
    recognition.onend = () => setIsListening(false);
    recognition.start();
  };

  const copySql = (sql: string) => {
    navigator.clipboard.writeText(sql);
    setCopiedSql(true);
    setTimeout(() => setCopiedSql(false), 2000);
  };

  const handleQuery = async (e?: React.FormEvent, directQ?: string) => {
    if (e) e.preventDefault();
    const q = directQ || question;
    if (!q.trim() || loading) return;

    // Add user message
    const userMsg = { role: "user", content: q };
    const assistantMsg = { role: "assistant", content: "", sql: "", results: null, error: "", attempts: 0, latency: 0, loading: true, explanation: "" };
    setMessages(prev => [...prev, userMsg, assistantMsg]);
    setQuestion("");
    setLoading(true);

    try {
      const res = await fetch("http://localhost:8000/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q, history: chatHistory }),
      });
      if (!res.body) throw new Error("No response body");
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        let boundary = buffer.indexOf("\n\n");
        while (boundary !== -1) {
          const line = buffer.slice(0, boundary);
          buffer = buffer.slice(boundary + 2);
          if (line.startsWith("data: ")) {
            try {
              const data = JSON.parse(line.substring(6));
              setMessages(prev => {
                const updated = [...prev];
                const last = { ...updated[updated.length - 1] };
                if (data.type === "status") last.content = data.message;
                else if (data.type === "error") { last.error = data.error; last.sql = data.sql || ""; last.attempts = data.attempts; last.loading = false; }
                else if (data.type === "result") { last.sql = data.sql; last.results = data.results; last.attempts = data.attempts; last.latency = data.latency_ms; last.content = ""; setChatHistory(p => [...p, { question: q, sql: data.sql }]); }
                else if (data.type === "explanation_token") last.explanation = (last.explanation || "") + data.token;
                else if (data.type === "suggestions") { if (Array.isArray(data.data) && data.data.length > 0) setSuggestions(data.data); }
                else if (data.type === "done") { last.loading = false; }
                updated[updated.length - 1] = last;
                return updated;
              });
            } catch {}
          }
          boundary = buffer.indexOf("\n\n");
        }
      }
    } catch (err: any) {
      setMessages(prev => {
        const updated = [...prev];
        const last = { ...updated[updated.length - 1] };
        last.error = err.message || "Failed to connect to backend.";
        last.loading = false;
        updated[updated.length - 1] = last;
        return updated;
      });
    } finally {
      setLoading(false);
      setMessages(prev => {
        const updated = [...prev];
        const last = { ...updated[updated.length - 1] };
        last.loading = false;
        updated[updated.length - 1] = last;
        return updated;
      });
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleQuery();
    }
  };

  const newChat = () => {
    setMessages([]);
    setChatHistory([]);
    setQuestion("");
    setSuggestions([
      "How many total products are there?",
      "What is the average order amount?",
      "Show me the top 5 customers by revenue",
    ]);
  };

  const hasMessages = messages.length > 0;

  return (
    <div className="h-screen flex bg-background text-foreground overflow-hidden">
      {/* ─── Sidebar ─── */}
      {sidebarOpen && (
        <aside className="w-[260px] flex-shrink-0 bg-sidebar-bg border-r border-sidebar-border flex flex-col h-full">
          {/* New Chat Button */}
          <div className="p-3">
            <button
              onClick={newChat}
              className="w-full flex items-center gap-2 px-3 py-2.5 rounded-lg border border-border text-sm font-medium hover:bg-muted transition-colors"
            >
              <IconPlus />
              New chat
            </button>
          </div>

          {/* Schema Section */}
          <div className="flex-1 overflow-y-auto px-3">
            <button
              onClick={() => setSchemaExpanded(!schemaExpanded)}
              className="w-full flex items-center gap-2 px-2 py-2 text-xs font-medium text-muted-foreground uppercase tracking-wider hover:text-foreground transition-colors"
            >
              <IconChevron open={schemaExpanded} />
              <IconDatabase />
              Schema ({schema.length} tables)
            </button>

            {schemaExpanded && (
              <div className="pl-4 space-y-0.5 mb-4">
                {schema.map((table: any, idx: number) => (
                  <div key={idx}>
                    <button
                      onClick={() => setExpandedTable(expandedTable === idx ? null : idx)}
                      className="w-full text-left px-2 py-1.5 text-[13px] font-mono text-muted-foreground hover:text-foreground hover:bg-muted rounded transition-colors flex items-center gap-2"
                    >
                      <span className="truncate">{table.table}</span>
                    </button>
                    {expandedTable === idx && table.description && (
                      <p className="px-2 py-1 text-[11px] text-muted-foreground leading-relaxed border-l-2 border-border ml-2 mb-1">
                        {table.description}
                      </p>
                    )}
                  </div>
                ))}
                {schema.length === 0 && (
                  <p className="px-2 py-2 text-xs text-muted-foreground">No schema loaded</p>
                )}
              </div>
            )}
          </div>

          {/* Sidebar Footer */}
          <div className="border-t border-sidebar-border p-3 space-y-1">
            <button
              onClick={loadHistory}
              className="w-full flex items-center gap-2 px-2 py-2 text-sm text-muted-foreground hover:text-foreground hover:bg-muted rounded-lg transition-colors"
            >
              <IconHistory />
              History
            </button>
            <button
              onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
              className="w-full flex items-center gap-2 px-2 py-2 text-sm text-muted-foreground hover:text-foreground hover:bg-muted rounded-lg transition-colors"
            >
              {mounted && theme === "dark" ? <IconSun /> : <IconMoon />}
              {mounted && theme === "dark" ? "Light mode" : "Dark mode"}
            </button>
            <div className="flex items-center gap-1.5 px-2 py-1.5 text-[11px] text-muted-foreground">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
              On-premise · No data leaves your machine
            </div>
          </div>
        </aside>
      )}

      {/* ─── Main Area ─── */}
      <main className="flex-1 flex flex-col h-full min-w-0">

        {/* ─── Empty State ─── */}
        {!hasMessages && (
          <div className="flex-1 flex flex-col items-center justify-center px-6">
            <div className="max-w-2xl w-full text-center">
              <h1 className="text-3xl font-semibold mb-2 tracking-tight">AskBase</h1>
              <p className="text-muted-foreground text-base mb-10">
                Ask questions about your database in plain English.
              </p>

              {/* Suggestions */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-12">
                {suggestions.map((s, i) => (
                  <button
                    key={i}
                    onClick={() => handleQuery(undefined, s)}
                    className="text-left p-4 rounded-xl border border-border hover:bg-muted transition-colors group"
                  >
                    <p className="text-sm text-foreground leading-snug">{s}</p>
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ─── Chat Messages ─── */}
        {hasMessages && (
          <div className="flex-1 overflow-y-auto">
            <div className="max-w-3xl mx-auto px-6 py-8 space-y-6">
              {messages.map((msg, i) => (
                <div key={i} className="animate-fade-in">
                  {msg.role === "user" ? (
                    /* User Message */
                    <div className="flex justify-end">
                      <div className="bg-muted rounded-2xl rounded-br-md px-4 py-3 max-w-[80%]">
                        <p className="text-sm leading-relaxed">{msg.content}</p>
                      </div>
                    </div>
                  ) : (
                    /* Assistant Message */
                    <div className="space-y-4">
                      {/* Loading / Status */}
                      {msg.loading && msg.content && (
                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                          <div className="w-4 h-4 border-2 border-muted-foreground/30 border-t-muted-foreground rounded-full animate-spin" />
                          {msg.content}
                        </div>
                      )}
                      {msg.loading && !msg.content && (
                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                          <div className="w-4 h-4 border-2 border-muted-foreground/30 border-t-muted-foreground rounded-full animate-spin" />
                          Thinking...
                        </div>
                      )}

                      {/* Error */}
                      {msg.error && (
                        <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-4">
                          <p className="text-sm text-destructive font-mono whitespace-pre-wrap">{msg.error}</p>
                        </div>
                      )}

                      {/* SQL Block */}
                      {msg.sql && (
                        <div className="sql-block">
                          <div className="flex items-center justify-between px-4 py-2.5 border-b border-border bg-muted/50">
                            <div className="flex items-center gap-2 text-xs text-muted-foreground font-medium">
                              <IconCode />
                              SQL
                              {msg.latency > 0 && (
                                <span className="ml-2 text-emerald-600 dark:text-emerald-400">{msg.latency}ms</span>
                              )}
                              {msg.attempts > 1 && (
                                <span className="ml-1 text-amber-600 dark:text-amber-400">{msg.attempts} attempts</span>
                              )}
                            </div>
                            <button
                              onClick={() => copySql(msg.sql)}
                              className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
                            >
                              {copiedSql ? <><IconCheck /> Copied</> : <><IconCopy /> Copy</>}
                            </button>
                          </div>
                          <pre className="text-sm font-mono text-foreground leading-relaxed whitespace-pre-wrap p-4">
                            {msg.sql}
                          </pre>
                        </div>
                      )}

                      {/* Explanation */}
                      {msg.explanation && !msg.loading && (
                        <p className="text-sm text-foreground leading-relaxed">{msg.explanation}</p>
                      )}
                      {msg.explanation && msg.loading && (
                        <p className="text-sm text-foreground leading-relaxed typing-cursor">{msg.explanation}</p>
                      )}

                      {/* Results */}
                      {msg.results && (
                        <div className="border border-border rounded-lg overflow-hidden">
                          {/* Tab bar */}
                          <div className="flex items-center border-b border-border bg-muted/30">
                            <button
                              onClick={() => setActiveTab("table")}
                              className={`flex items-center gap-1.5 px-4 py-2.5 text-xs font-medium transition-colors border-b-2 ${
                                activeTab === "table"
                                  ? "border-foreground text-foreground"
                                  : "border-transparent text-muted-foreground hover:text-foreground"
                              }`}
                            >
                              <IconTable /> Table
                            </button>
                            <button
                              onClick={() => setActiveTab("chart")}
                              className={`flex items-center gap-1.5 px-4 py-2.5 text-xs font-medium transition-colors border-b-2 ${
                                activeTab === "chart"
                                  ? "border-foreground text-foreground"
                                  : "border-transparent text-muted-foreground hover:text-foreground"
                              }`}
                            >
                              <IconChart /> Chart
                            </button>
                            <span className="ml-auto pr-4 text-[11px] text-muted-foreground font-mono">
                              {msg.results.rows?.length || 0} rows
                            </span>
                          </div>

                          {activeTab === "table" ? (
                            <div className="max-h-[400px] overflow-auto">
                              <table className="w-full text-left">
                                <thead className="bg-muted/50 sticky top-0">
                                  <tr>
                                    {msg.results.columns?.map((col: string) => (
                                      <th key={col} className="px-4 py-2.5 text-[11px] font-semibold text-muted-foreground uppercase tracking-wider whitespace-nowrap border-b border-border">
                                        {col}
                                      </th>
                                    ))}
                                  </tr>
                                </thead>
                                <tbody className="divide-y divide-border">
                                  {msg.results.rows?.map((row: any, ri: number) => (
                                    <tr key={ri} className="hover:bg-muted/30 transition-colors">
                                      {msg.results.columns?.map((col: string) => (
                                        <td key={col} className="px-4 py-2.5 text-sm font-mono whitespace-nowrap">
                                          {row[col] === null || row[col] === undefined
                                            ? <span className="text-muted-foreground/40 italic text-xs">null</span>
                                            : typeof row[col] === "number"
                                              ? <span className="text-accent-brand">{row[col].toLocaleString()}</span>
                                              : String(row[col])
                                          }
                                        </td>
                                      ))}
                                    </tr>
                                  ))}
                                  {(!msg.results.rows || msg.results.rows.length === 0) && (
                                    <tr>
                                      <td colSpan={msg.results.columns?.length || 1} className="px-4 py-8 text-center text-sm text-muted-foreground">
                                        Query returned no results.
                                      </td>
                                    </tr>
                                  )}
                                </tbody>
                              </table>
                            </div>
                          ) : (
                            <div className="p-6 h-[320px]">
                              {(() => {
                                let xKey = "", yKey = "";
                                if (msg.results.columns) {
                                  for (const col of msg.results.columns) {
                                    const val = msg.results.rows[0]?.[col];
                                    if (typeof val === "number" && !yKey) yKey = col;
                                    else if (!xKey) xKey = col;
                                  }
                                  if (!xKey && msg.results.columns.length > 0) xKey = msg.results.columns[0];
                                  if (!yKey && msg.results.columns.length > 1) yKey = msg.results.columns[1];
                                }
                                if (xKey && yKey) {
                                  return (
                                    <ResponsiveContainer width="100%" height="100%">
                                      <BarChart data={msg.results.rows} margin={{ top: 10, right: 10, left: -10, bottom: 20 }}>
                                        <CartesianGrid strokeDasharray="3 3" opacity={0.15} vertical={false} />
                                        <XAxis dataKey={xKey} fontSize={11} tickLine={false} axisLine={false} angle={-30} textAnchor="end" height={50} stroke="var(--muted-foreground)" />
                                        <YAxis fontSize={11} tickLine={false} axisLine={false} stroke="var(--muted-foreground)" tickFormatter={(v) => v >= 1000 ? `${(v/1000).toFixed(1)}k` : v} />
                                        <RechartsTooltip
                                          cursor={false}
                                          contentStyle={{
                                            backgroundColor: 'var(--card)',
                                            border: '1px solid var(--border)',
                                            borderRadius: '8px',
                                            fontSize: '12px',
                                            color: 'var(--foreground)',
                                            boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
                                          }}
                                          labelStyle={{ color: 'var(--foreground)', fontWeight: 600, marginBottom: '4px' }}
                                          itemStyle={{ color: 'var(--muted-foreground)' }}
                                        />
                                        <Bar dataKey={yKey} radius={[4, 4, 0, 0]} maxBarSize={48}>
                                          {msg.results.rows?.map((_: any, idx: number) => (
                                            <Cell key={idx} fill={CHART_COLORS[idx % CHART_COLORS.length]} />
                                          ))}
                                        </Bar>
                                      </BarChart>
                                    </ResponsiveContainer>
                                  );
                                }
                                return (
                                  <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
                                    Not enough numeric data to visualize.
                                  </div>
                                );
                              })()}
                            </div>
                          )}
                        </div>
                      )}

                      {/* Follow-up suggestions */}
                      {msg.results && !msg.loading && suggestions.length > 0 && (
                        <div className="flex flex-wrap gap-2 pt-2">
                          {suggestions.map((s, si) => (
                            <button
                              key={si}
                              onClick={() => handleQuery(undefined, s)}
                              className="text-xs px-3 py-1.5 rounded-full border border-border text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                            >
                              {s}
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>
          </div>
        )}

        {/* ─── Input Area ─── */}
        <div className={`border-t border-border bg-background px-6 py-4 ${!hasMessages ? '' : ''}`}>
          <div className="max-w-3xl mx-auto">
            <form onSubmit={handleQuery}>
              <div className="relative flex items-end bg-muted rounded-2xl border border-border focus-within:border-foreground/30 transition-colors">
                <textarea
                  ref={inputRef}
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Ask about your data..."
                  disabled={loading}
                  rows={1}
                  className="flex-1 bg-transparent resize-none px-4 py-3.5 text-sm outline-none placeholder:text-muted-foreground min-h-[48px] max-h-[200px]"
                  style={{ lineHeight: '1.5' }}
                />
                <div className="flex items-center gap-1 pr-2 pb-2">
                  <button
                    type="button"
                    onClick={toggleListening}
                    className={`p-2 rounded-lg transition-colors ${
                      isListening ? "text-destructive bg-destructive/10" : "text-muted-foreground hover:text-foreground hover:bg-background"
                    }`}
                    title="Voice input"
                  >
                    <IconMic />
                  </button>
                  <button
                    type="submit"
                    disabled={loading || !question.trim()}
                    className="p-2 rounded-lg bg-foreground text-background disabled:opacity-30 disabled:cursor-not-allowed hover:opacity-80 transition-opacity"
                  >
                    <IconSend />
                  </button>
                </div>
              </div>
            </form>
            <p className="text-[11px] text-muted-foreground text-center mt-2">
              AskBase generates SQL from natural language. Always verify results.
            </p>
          </div>
        </div>
      </main>

      {/* ─── History Modal ─── */}
      {historyOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm" onClick={() => setHistoryOpen(false)}>
          <div className="bg-card border border-border shadow-xl w-full max-w-2xl max-h-[80vh] rounded-2xl flex flex-col mx-4 animate-fade-in" onClick={(e) => e.stopPropagation()}>
            <div className="px-6 py-4 border-b border-border flex justify-between items-center">
              <h2 className="text-base font-semibold">Query History</h2>
              <button onClick={() => setHistoryOpen(false)} className="p-1 rounded hover:bg-muted transition-colors">
                <IconX />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-6 space-y-4">
              {history.length === 0 ? (
                <p className="text-center py-12 text-sm text-muted-foreground">No queries in history yet.</p>
              ) : (
                history.map((h, i) => (
                  <button
                    key={i}
                    onClick={() => { setHistoryOpen(false); handleQuery(undefined, h.question); }}
                    className="w-full text-left p-4 rounded-lg border border-border hover:bg-muted transition-colors space-y-2"
                  >
                    <div className="flex justify-between items-start gap-3">
                      <p className="text-sm font-medium">{h.question}</p>
                      <span className={`text-[10px] font-medium uppercase px-2 py-0.5 rounded ${
                        h.status === "Success" ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400" : "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"
                      }`}>
                        {h.status}
                      </span>
                    </div>
                    <pre className="text-xs font-mono text-muted-foreground truncate">{h.generated_sql || "N/A"}</pre>
                  </button>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
