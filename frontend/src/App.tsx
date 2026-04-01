import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Shield, Activity, Users, AlertTriangle, CheckCircle, ChevronDown, ActivitySquare } from "lucide-react";
import Background3D from "./components/Background3D";

// Types
type Incident = {
  id: number;
  slack_message: string;
  user: string;
  severity: number;
  ai_reasoning: string;
  github_confirmed: boolean;
  timestamp: string;
};

type Analytics = {
  total: number;
  severity_distribution: { high: number; medium: number; low: number };
  top_users: { user: string; count: number }[];
};

// Config for glassmorphic animation variables
const slideUp = {
  initial: { opacity: 0, y: 30 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, scale: 0.95 },
  transition: { duration: 0.5, ease: [0.22, 1, 0.36, 1] as const },
};

export default function App() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const [incRes, anaRes] = await Promise.all([
          fetch("/api/incidents"),
          fetch("/api/analytics"),
        ]);
        if (!incRes.ok) throw new Error("Not Authenticated");
        
        setIncidents(await incRes.json());
        setAnalytics(await anaRes.json());
        setLoading(false);
      } catch (err) {
        // If forbidden or unauth, send back to login
        window.location.href = "/login";
      }
    }
    fetchData();
    const interval = setInterval(fetchData, 10000); // 10s auto refresh
    return () => clearInterval(interval);
  }, []);

  if (loading) return (
    <div className="flex h-screen w-screen items-center justify-center bg-bg0">
      <div className="w-12 h-12 border-4 border-primary border-t-transparent rounded-full animate-spin shadow-[0_0_20px_#8b5cf6]"></div>
    </div>
  );

  return (
    <>
      <Background3D />
      
      <main className="relative z-10 w-full max-w-7xl mx-auto px-6 py-12 flex flex-col gap-8 min-h-screen">
        
        {/* Header Header */}
        <motion.header 
          {...slideUp}
          className="flex justify-between items-center"
        >
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-2xl flex items-center justify-center shadow-[0_0_30px_rgba(99,102,241,0.5)] animate-pulse">
              <Shield className="w-8 h-8 text-white" />
            </div>
            <div>
              <h1 className="text-3xl font-extrabold tracking-tight glow-text leading-tight">Guardian AI</h1>
              <p className="text-gray-400 font-medium text-sm">Enterprise Data Security Engine</p>
            </div>
          </div>
          <div className="flex items-center gap-3 glass-panel px-5 py-2.5 rounded-full select-none cursor-pointer hover:bg-white/5 transition border-primary/20">
            <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 shadow-[0_0_10px_#10b981] animate-ping"></div>
            <span className="text-sm font-semibold tracking-wide text-gray-200">System Secure</span>
            <ChevronDown className="w-4 h-4 text-gray-400 ml-2" />
          </div>
        </motion.header>

        {/* Global Analytics Cards */}
        <motion.div 
          className="grid grid-cols-1 md:grid-cols-4 gap-4"
          initial="initial" animate="animate" variants={{
            animate: { transition: { staggerChildren: 0.1 }}
          }}
        >
          <StatCard title="Total Scanned" value={analytics?.total} icon={<Activity />} color="text-indigo-400" bg="bg-indigo-500/10" border="border-indigo-500/20" />
          <StatCard title="Critical Risk" value={analytics?.severity_distribution.high} icon={<AlertTriangle />} color="text-red-400" bg="bg-red-500/10" border="border-red-500/20" />
          <StatCard title="Active Users" value={analytics?.top_users.length} icon={<Users />} color="text-emerald-400" bg="bg-emerald-500/10" border="border-emerald-500/20" />
          <StatCard title="Confirmed Leaks" value={incidents.filter(i => i.github_confirmed).length} icon={<CheckCircle />} color="text-purple-400" bg="bg-purple-500/10" border="border-purple-500/20" />
        </motion.div>

        {/* Incidents Table */}
        <motion.div {...slideUp} transition={{ delay: 0.4 }} className="glass-panel overflow-hidden mt-4">
          <div className="p-6 border-b border-white/5">
            <h2 className="text-xl font-bold flex items-center gap-2 text-white">
              <ActivitySquare className="text-primary w-5 h-5"/> Live Incident Stream
            </h2>
          </div>
          
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-white/5 border-b border-white/5">
                  <th className="p-4 font-semibold text-xs tracking-wider text-gray-400 uppercase">Detection Time</th>
                  <th className="p-4 font-semibold text-xs tracking-wider text-gray-400 uppercase">Source ID</th>
                  <th className="p-4 font-semibold text-xs tracking-wider text-gray-400 uppercase">Risk Reason</th>
                  <th className="p-4 font-semibold text-xs tracking-wider text-gray-400 uppercase text-center">Severity</th>
                  <th className="p-4 font-semibold text-xs tracking-wider text-gray-400 uppercase text-center">Validated</th>
                </tr>
              </thead>
              <tbody>
                <AnimatePresence>
                  {incidents.map((inc) => (
                    <motion.tr 
                      key={inc.id}
                      layout
                      initial={{ opacity: 0, y: 15 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0 }}
                      whileHover={{ backgroundColor: "rgba(99,102,241,0.06)" }}
                      className="border-b border-white/5 cursor-pointer hover:bg-white/5 transition"
                    >
                      <td className="p-4 whitespace-nowrap text-sm text-gray-400 font-mono">
                        {new Date(inc.timestamp).toLocaleString(undefined, { hour: 'numeric', minute: 'numeric', second: 'numeric', month: 'short', day: 'numeric'})}
                      </td>
                      <td className="p-4 text-sm font-semibold text-secondary decoration-secondary/30 hover:underline">{inc.user}</td>
                      <td className="p-4 text-sm max-w-xs truncate text-gray-300" title={inc.ai_reasoning}>{inc.ai_reasoning}</td>
                      <td className="p-4 text-center">
                        <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-bold border ${
                          inc.severity >= 7 ? "bg-red-500/20 text-red-500 border-red-500/30" :
                          inc.severity >= 4 ? "bg-amber-500/20 text-amber-500 border-amber-500/30" :
                          "bg-emerald-500/20 text-emerald-500 border-emerald-500/30"
                        }`}>
                          {inc.severity >= 7 ? "🔴 HIGH" : inc.severity >= 4 ? "🟠 MED" : "🟡 LOW"} — {inc.severity}/10
                        </span>
                      </td>
                      <td className="p-4 text-center">
                        {inc.github_confirmed ? (
                           <span className="bg-purple-500/20 text-purple-400 border border-purple-500/30 px-3 py-1 rounded-full text-xs font-bold font-mono">GH MATCH</span>
                        ) : (
                           <span className="text-gray-500 text-xs font-semibold">PENDING</span>
                        )}
                      </td>
                    </motion.tr>
                  ))}
                </AnimatePresence>
                {incidents.length === 0 && (
                  <tr>
                    <td colSpan={5} className="p-12 text-center text-gray-500">
                      <Shield className="w-12 h-12 mx-auto mb-3 opacity-20" />
                      <p>No incidents detected on the network.</p>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </motion.div>
      </main>
    </>
  );
}

// Subcomponent for simple staggering
function StatCard({ title, value, icon, color, bg, border }: any) {
  return (
    <motion.div variants={slideUp} className="glass-panel p-6 flex flex-col gap-4 relative overflow-hidden group">
      <div className={`absolute -right-4 -top-4 w-24 h-24 rounded-full ${bg} blur-2xl group-hover:scale-150 transition-transform duration-700 ease-out`}></div>
      <div className="flex justify-between items-start relative z-10">
        <h3 className="text-gray-400 font-semibold text-sm tracking-wide">{title}</h3>
        <span className={`p-2 rounded-xl ${bg} ${border} border ${color}`}>{icon}</span>
      </div>
      <p className="text-4xl font-extrabold text-white tracking-tight relative z-10">{value ?? 0}</p>
    </motion.div>
  )
}
