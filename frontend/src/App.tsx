import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Shield, Activity, Users, AlertCircle, CheckCircle2, LayoutDashboard, Database, History, ExternalLink } from "lucide-react";
import Background3D from "./components/Background3D";

// Types
type Incident = {
  id: number;
  slack_message: string;
  user: string;
  severity: number;
  type: string;
  ai_reasoning: string;
  github_confirmed: boolean;
  timestamp: string;
  policy_url: string;
};

type Analytics = {
  total: number;
  severity_distribution: { high: number; medium: number; low: number };
  top_users: { user: string; count: number }[];
};

// Smooth UI entry animation
const containerVariants = {
  hidden: { opacity: 0 },
  visible: { 
    opacity: 1, 
    transition: { staggerChildren: 0.1, delayChildren: 0.2 } 
  }
};

const itemVariants = {
  hidden: { opacity: 0, y: 15 },
  visible: { 
    opacity: 1, 
    y: 0, 
    transition: { type: "spring", stiffness: 400, damping: 25 } 
  }
};

export default function App() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [loading, setLoading] = useState(true);

  async function fetchData() {
    try {
      const [incRes, anaRes] = await Promise.all([
        fetch("/api/incidents"),
        fetch("/api/analytics"),
      ]);
      if (!incRes.ok) throw new Error("UNAUTHORIZED");
      setIncidents(await incRes.json());
      setAnalytics(await anaRes.json());
      setLoading(false);
    } catch (err) {
      window.location.href = "/login";
    }
  }

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 15000); // Polling 15s
    return () => clearInterval(interval);
  }, []);

  if (loading) return (
    <div className="flex h-screen w-screen items-center justify-center bg-slate-950">
      <div className="flex flex-col items-center gap-4">
        <div className="w-10 h-10 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
        <span className="text-slate-400 font-medium tracking-tight">Authenticating Guardian Session...</span>
      </div>
    </div>
  );

  return (
    <div className="relative min-h-screen bg-slate-950 text-slate-100 overflow-hidden">
      <div className="absolute inset-0 bg-grid opacity-20 pointer-events-none" />
      <Background3D />
      
      <main className="relative z-10 max-w-7xl mx-auto px-6 py-8 flex flex-col gap-8">
        
        {/* Navigation / Header */}
        <motion.nav 
          initial={{ opacity: 0, y: -20 }} 
          animate={{ opacity: 1, y: 0 }}
          className="flex justify-between items-center py-2"
        >
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-indigo-600 rounded-lg flex items-center justify-center shadow-lg shadow-indigo-500/20">
              <Shield className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white tracking-tight leading-none uppercase">Guardian AI</h1>
              <span className="text-[10px] text-indigo-400 font-bold tracking-[0.2em] uppercase">Enterprise Data Security</span>
            </div>
          </div>
          
          <div className="flex items-center gap-6">
            <a href="/policy" target="_blank" className="text-sm font-medium text-slate-400 hover:text-white transition-colors flex items-center gap-1.5">
              Security Policy <ExternalLink size={14}/>
            </a>
            <div className="h-4 w-px bg-slate-800" />
            <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-900 border border-slate-800 rounded-full">
              <span className="w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_8px_#10b981]"></span>
              <span className="text-xs font-semibold text-slate-300">SYSTEM ONLINE</span>
            </div>
          </div>
        </motion.nav>

        {/* Global Analytics Section */}
        <motion.div 
          variants={containerVariants} 
          initial="hidden" 
          animate="visible"
          className="grid grid-cols-1 md:grid-cols-4 gap-6"
        >
          <StatCard title="Security Sweeps" value={analytics?.total} icon={<Activity className="w-5 h-5"/>} trend="+5.2%" />
          <StatCard title="Critical Risks" value={analytics?.severity_distribution.high} icon={<AlertCircle className="w-5 h-5"/>} color="text-rose-500" />
          <StatCard title="Monitored Users" value={analytics?.top_users.length} icon={<Users className="w-5 h-5"/>} />
          <StatCard title="Database Synced" value="100%" icon={<Database className="w-5 h-5"/>} color="text-emerald-500" />
        </motion.div>

        {/* Dynamic Threat Feed */}
        <motion.section 
          variants={itemVariants}
          initial="hidden"
          animate="visible"
          className="flex flex-col gap-4"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-white">
              <LayoutDashboard size={18} className="text-indigo-400"/>
              <h2 className="text-lg font-bold">Real-time Incident Feed</h2>
            </div>
            <div className="flex items-center gap-2 text-xs text-slate-500 font-mono">
              <History size={14}/> LAST UPDATED: {new Date().toLocaleTimeString()}
            </div>
          </div>

          <div className="card-panel overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-slate-800/30 text-slate-400 text-[11px] font-bold uppercase tracking-wider">
                    <th className="py-4 px-6 border-b border-slate-800">Timestamp (UTC)</th>
                    <th className="py-4 px-6 border-b border-slate-800">Contributor</th>
                    <th className="py-4 px-6 border-b border-slate-800">Observation Diagnostic</th>
                    <th className="py-4 px-6 border-b border-slate-800 text-center">Threat Level</th>
                    <th className="py-4 px-6 border-b border-slate-800 text-center">Outcome</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800">
                  <AnimatePresence initial={false}>
                    {incidents.slice(0, 10).map((inc) => (
                      <motion.tr 
                        key={inc.id}
                        layout
                        initial={{ opacity: 0, x: -5 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0 }}
                        className="group hover:bg-slate-800/20 transition-colors"
                      >
                        <td className="py-4 px-6 text-sm text-slate-400 font-mono">
                          {new Date(inc.timestamp).toISOString().replace("T", " ").slice(0, 19)}
                        </td>
                        <td className="py-4 px-6 text-sm font-semibold text-slate-200">@{inc.user}</td>
                        <td className="py-4 px-6 text-sm text-slate-400 italic max-w-sm" title={inc.ai_reasoning}>
                          "{inc.ai_reasoning.slice(0, 70)}..."
                        </td>
                        <td className="py-4 px-6 text-center">
                          <SeverityBadge score={inc.severity} />
                        </td>
                        <td className="py-4 px-6 text-center">
                          {inc.github_confirmed ? (
                            <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-rose-500/10 text-rose-500 border border-rose-500/20 text-[10px] font-bold">
                              EXPOSED ON GITHUB
                            </div>
                          ) : (
                            <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-800 text-slate-400 text-[10px] font-bold">
                              INTERNAL RISK
                            </div>
                          )}
                        </td>
                      </motion.tr>
                    ))}
                  </AnimatePresence>
                </tbody>
              </table>
              {incidents.length === 0 && (
                <div className="py-24 flex flex-col items-center justify-center text-slate-500 gap-3">
                  <CheckCircle2 size={40} className="text-emerald-500/40 opacity-50"/>
                  <span className="font-medium">All communication channels are currently clear.</span>
                </div>
              )}
            </div>
          </div>
        </motion.section>
      </main>
    </div>
  );
}

function SeverityBadge({ score }: { score: number }) {
  const getSeverity = () => {
    if (score >= 7) return { label: "CRITICAL", classes: "bg-rose-500/10 text-rose-500 border-rose-500/20 shadow-rose-500/10" };
    if (score >= 4) return { label: "WARNING", classes: "bg-amber-500/10 text-amber-500 border-amber-500/20 shadow-amber-500/10" };
    return { label: "SAFE", classes: "bg-emerald-500/10 text-emerald-500 border-emerald-500/20 shadow-emerald-500/10" };
  };
  const { label, classes } = getSeverity();
  return (
    <div className={`inline-flex items-center px-3 py-1 rounded-full text-[10px] font-black border shadow-inner ${classes}`}>
      {label} — {score}/10
    </div>
  );
}

function StatCard({ title, value, icon, color = "text-indigo-500", trend = "" }: any) {
  return (
    <motion.div 
      variants={itemVariants}
      className="card-panel p-6 flex flex-col gap-2 relative overflow-hidden group"
    >
      <div className={`absolute -right-6 -bottom-6 w-24 h-24 rounded-full bg-indigo-500/5 blur-3xl group-hover:bg-indigo-500/10 transition-colors`}/>
      
      <div className="flex justify-between items-center text-slate-500">
        <h3 className="text-[11px] font-black uppercase tracking-widest">{title}</h3>
        <div className={`p-2 bg-slate-800 rounded-lg ${color}`}>{icon}</div>
      </div>
      
      <div className="flex items-end gap-3 mt-1">
        <span className="text-3xl font-extrabold text-white tracking-tighter leading-none">{value ?? 0}</span>
        {trend && (
           <span className="text-emerald-500 text-[10px] font-bold mb-1.5">{trend}</span>
        )}
      </div>
    </motion.div>
  );
}
