"use client";

import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Send, CheckCircle, AlertCircle, Loader2, Zap, BarChart3, Mail, RefreshCcw } from "lucide-react";

// Fallback to localhost if ENV is not set
const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

export default function Dashboard() {
  const [isBackendLive, setIsBackendLive] = useState(false);
  const [isCheckingHealth, setIsCheckingHealth] = useState(true);
  const [isTriggering, setIsTriggering] = useState(false);
  const [lastResult, setLastResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");

  // Poll health endpoint
  const checkHealth = useCallback(async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/health`);
      if (response.ok) {
        setIsBackendLive(true);
        setError(null);
      } else {
        setIsBackendLive(false);
      }
    } catch (err) {
      setIsBackendLive(false);
    } finally {
      setIsCheckingHealth(false);
    }
  }, []);

  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 10000); // Check every 10s
    return () => clearInterval(interval);
  }, [checkHealth]);

  const handleTrigger = async () => {
    if (!isBackendLive || isTriggering) return;

    setIsTriggering(true);
    setError(null);
    try {
      const response = await fetch(`${BACKEND_URL}/trigger`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: query.trim() || undefined }),
      });
      const data = await response.json();
      if (response.ok) {
        setLastResult(data);
      } else {
        setError(data.detail || "Failed to trigger outreach.");
      }
    } catch (err) {
      setError("Connection lost. Backend might have timed out.");
    } finally {
      setIsTriggering(false);
    }
  };

  return (
    <div className="min-h-screen bg-black text-white selection:bg-orange-500/30 overflow-x-hidden font-sans">
      {/* Cinematic Background Gradient */}
      <div className="fixed inset-0 bg-[radial-gradient(circle_at_50%_50%,_rgba(255,100,0,0.05),_transparent_70%)] pointer-events-none" />
      
      <main className="max-w-6xl mx-auto px-6 py-20 relative z-10">
        {/* Header */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-col md:flex-row justify-between items-start md:items-center mb-16 gap-6"
        >
          <div>
            <h1 className="text-4xl md:text-5xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-orange-400 to-amber-600 mb-2">
              The Latest Buzz
            </h1>
            <p className="text-zinc-400 text-lg">AI-Powered Influencer Outreach Agent</p>
          </div>

          <div className="flex items-center gap-4 bg-zinc-900/50 backdrop-blur-xl border border-zinc-800 px-5 py-3 rounded-2xl shadow-xl">
            <div className="flex flex-col">
              <span className="text-[10px] uppercase tracking-widest text-zinc-500 font-bold">System Status</span>
              <div className="flex items-center gap-2 mt-1">
                <div className={`w-2.5 h-2.5 rounded-full ${isBackendLive ? 'bg-green-500 animate-pulse shadow-[0_0_8px_rgba(34,197,94,0.6)]' : 'bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.6)]'}`} />
                <span className={`text-sm font-medium ${isBackendLive ? 'text-zinc-200' : 'text-zinc-400'}`}>
                  {isCheckingHealth ? "Checking..." : isBackendLive ? "Backend Online" : "Backend Sleeping"}
                </span>
              </div>
            </div>
            {!isBackendLive && (
              <button 
                onClick={checkHealth}
                className="p-2 hover:bg-zinc-800 rounded-lg transition-colors group"
                title="Refresh Status"
              >
                <RefreshCcw className={`w-4 h-4 text-zinc-500 group-hover:text-orange-400 ${isCheckingHealth ? 'animate-spin' : ''}`} />
              </button>
            )}
          </div>
        </motion.div>

        {/* Action Center */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          <motion.div 
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.1 }}
            className="lg:col-span-12"
          >
            <div className="bg-gradient-to-br from-zinc-900/80 to-black p-8 rounded-3xl border border-zinc-800 shadow-2xl relative overflow-hidden group">
              <div className="absolute top-0 right-0 p-8 opacity-5">
                <Zap className="w-48 h-48 text-orange-500" />
              </div>

              <div className="relative z-10">
                <h2 className="text-2xl font-semibold mb-6 flex items-center gap-3">
                  <Zap className="w-6 h-6 text-orange-500" />
                  Control Hub
                </h2>
                
                <div className="flex flex-col gap-6 md:gap-8">
                  <div className="flex flex-col md:flex-row items-start md:items-center gap-8 md:gap-16">
                    <div className="flex-1 space-y-4">
                      <p className="text-zinc-400 leading-relaxed max-w-xl text-lg">
                        Start the daily outreach cycle. The agent will research Indian startups, identify decision-makers on Apollo, and deliver personalized pitches via Resend using your verified template.
                      </p>
                      <div className="flex flex-wrap gap-3">
                        <span className="px-3 py-1 bg-zinc-800 rounded-full text-xs text-zinc-400 border border-zinc-700">Tavily Web Search</span>
                        <span className="px-3 py-1 bg-zinc-800 rounded-full text-xs text-zinc-400 border border-zinc-700">Apollo B2B Data</span>
                        <span className="px-3 py-1 bg-zinc-800 rounded-full text-xs text-zinc-400 border border-zinc-700">Resend Delivery</span>
                      </div>
                    </div>
                  </div>

                  {/* Query Input Section */}
                  <div className="flex flex-col md:flex-row items-end gap-6">
                    <div className="flex-1 w-full space-y-3">
                      <label className="text-sm font-semibold text-zinc-300 uppercase tracking-widest pl-1">Target Market Search (Custom Query)</label>
                      <input 
                        type="text" 
                        placeholder="e.g., upcoming B2B SaaS startups in Bangalore, new AI agencies..."
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        className="w-full bg-black/50 border border-zinc-700 focus:border-orange-500/80 rounded-2xl px-6 py-4 text-white outline-none transition-all focus:ring-4 focus:ring-orange-500/10 shadow-inner text-lg placeholder:text-zinc-600"
                        disabled={isTriggering}
                      />
                      <p className="text-xs text-zinc-500 pl-1 font-medium italic">Leave empty to use dynamic randomized search queries across major cities and niches.</p>
                    </div>

                    <div className="w-full md:w-auto flex flex-col pt-4">
                      <button
                        onClick={handleTrigger}
                        disabled={!isBackendLive || isTriggering}
                        className={`
                          relative w-full md:w-64 py-5 px-8 rounded-2xl font-bold text-lg transition-all duration-300 flex items-center justify-center gap-3
                          ${isBackendLive && !isTriggering 
                            ? 'bg-gradient-to-r from-orange-500 to-amber-600 text-white shadow-[0_8px_30px_rgb(249,115,22,0.3)] hover:scale-[1.02] active:scale-[0.98]' 
                            : 'bg-zinc-800 text-zinc-500 cursor-not-allowed border border-zinc-700'}
                        `}
                      >
                        {isTriggering ? (
                          <>
                            <Loader2 className="w-6 h-6 animate-spin" />
                            <span>Executing...</span>
                          </>
                        ) : (
                          <>
                            <Send className={`w-5 h-5 ${isBackendLive ? 'text-white' : 'text-zinc-600'}`} />
                            <span>Run Outreach</span>
                          </>
                        )}
                      </button>
                      {!isBackendLive && (
                        <p className="text-center text-xs text-orange-400/60 mt-3 font-medium animate-pulse uppercase tracking-wider">
                          Waiting for Render to wake up...
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>

          {/* Results Display */}
          <AnimatePresence mode="wait">
            {lastResult && (
              <motion.div 
                key="results"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95 }}
                className="lg:col-span-8"
              >
                <div className="bg-zinc-900/40 backdrop-blur-md rounded-3xl border border-zinc-800 p-8 shadow-2xl h-full">
                  <div className="flex items-center justify-between mb-8">
                    <h3 className="text-xl font-semibold flex items-center gap-2">
                       <Mail className="w-5 h-5 text-orange-400" />
                       Recent Outreach Logs
                    </h3>
                    <div className="px-3 py-1 bg-green-500/10 text-green-400 text-xs rounded-full border border-green-500/20 font-medium">
                      Latest Success
                    </div>
                  </div>

                  <div className="space-y-4 max-h-[400px] overflow-y-auto custom-scrollbar pr-2">
                    {lastResult.sent_emails.map((email: any, i: number) => (
                      <div key={i} className="flex items-center justify-between p-4 bg-zinc-800/30 rounded-xl border border-zinc-800/50">
                        <div className="flex flex-col">
                          <span className="text-sm font-semibold text-zinc-100">{email.company}</span>
                          <span className="text-xs text-zinc-500">{email.email}</span>
                        </div>
                        <div className="flex items-center gap-2 text-green-400">
                          <CheckCircle className="w-4 h-4" />
                          <span className="text-xs font-bold font-mono">SENT</span>
                        </div>
                      </div>
                    ))}
                  </div>

                  {lastResult.sent_emails.length === 0 && (
                    <div className="text-center py-12 text-zinc-500 bg-zinc-800/20 rounded-2xl border border-dashed border-zinc-700">
                      No emails were sent in this session.
                    </div>
                  )}
                </div>
              </motion.div>
            )}

            {lastResult && (
              <motion.div 
                key="stats"
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="lg:col-span-4"
              >
                <div className="bg-gradient-to-b from-zinc-900 to-black p-8 rounded-3xl border border-orange-500/30 shadow-[0_0_50px_rgba(249,115,22,0.1)] h-full flex flex-col justify-center items-center text-center">
                  <div className="w-20 h-20 bg-orange-500/10 rounded-full flex items-center justify-center mb-6 border border-orange-500/20">
                    <BarChart3 className="w-10 h-10 text-orange-500" />
                  </div>
                  <h4 className="text-5xl font-black text-white mb-2">{lastResult.emails_sent_count}</h4>
                  <p className="text-orange-400 uppercase tracking-[0.2em] font-black text-sm">Emails Delivered</p>
                  <p className="text-zinc-500 mt-6 text-sm italic leading-relaxed">
                    This run successfully identified and contacted {lastResult.emails_sent_count} high-priority targets.
                  </p>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {error && (
            <motion.div 
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              className="lg:col-span-12 p-4 bg-red-500/10 border border-red-500/30 rounded-2xl flex items-center gap-3 text-red-500"
            >
              <AlertCircle className="w-5 h-5 flex-shrink-0" />
              <span className="font-medium">{error}</span>
            </motion.div>
          )}
        </div>
      </main>

      {/* Global CSS for scrollbar */}
      <style jsx global>{`
        .custom-scrollbar::-webkit-scrollbar { width: 4px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: #333; border-radius: 10px; }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: #444; }
      `}</style>
    </div>
  );
}
