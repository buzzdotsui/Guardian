import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ShieldAlert, Crosshair, Cpu, TerminalSquare, AlertOctagon, CheckSquare } from "lucide-react";
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

// Harsh robotic snapping animation
const snapIn = {
  initial: { opacity: 0, scale: 0.98, filter: "blur(4px)" },
  animate: { opacity: 1, scale: 1, filter: "blur(0px)" },
  exit: { opacity: 0, scale: 0.98 },
  transition: { duration: 0.2, type: "tween" as const, ease: "circOut" as const },
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
        if (!incRes.ok) throw new Error("AUTH_FAIL");
        setIncidents(await incRes.json());
        setAnalytics(await anaRes.json());
        setLoading(false);
      } catch (err) {
        window.location.href = "/login";
      }
    }
    fetchData();
    const interval = setInterval(fetchData, 10000); // 10s auto refresh
    return () => clearInterval(interval);
  }, []);

  if (loading) return (
    <div className="flex h-screen w-screen items-center justify-center bg-black">
      <div className="font-mono text-hudCyan animate-pulse tracking-widest text-xl">[ INITIALIZING TELEMETRY... ]</div>
    </div>
  );

  return (
    <>
      <div className="crt-overlay" />
      <Background3D />
      
      {/* 1px static border surrounding viewport like a camera HUD */}
      <div className="fixed inset-4 border border-hudCyan/20 pointer-events-none z-50"></div>
      <div className="fixed top-4 left-4 w-4 h-4 border-l-2 border-t-2 border-hudCyan pointer-events-none z-50"></div>
      <div className="fixed top-4 right-4 w-4 h-4 border-r-2 border-t-2 border-hudCyan pointer-events-none z-50"></div>
      <div className="fixed bottom-4 left-4 w-4 h-4 border-l-2 border-b-2 border-hudCyan pointer-events-none z-50"></div>
      <div className="fixed bottom-4 right-4 w-4 h-4 border-r-2 border-b-2 border-hudCyan pointer-events-none z-50"></div>

      <main className="relative z-10 w-full max-w-7xl mx-auto px-10 py-16 flex flex-col gap-8 min-h-screen">
        
        {/* Mission Control Header */}
        <motion.header {...snapIn} className="flex justify-between items-end border-b-2 border-hudCyan/40 pb-4">
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 bg-hudCyan/10 border border-hudCyan/50 flex items-center justify-center relative">
               <Crosshair className="w-8 h-8 text-hudCyan animate-[spin_4s_linear_infinite]" />
               <div className="absolute top-0 left-0 w-2 h-2 bg-hudCyan"></div>
            </div>
            <div>
              <h1 className="text-4xl font-extrabold tracking-widest glow-text uppercase">Guardian Core</h1>
              <p className="text-hudCyan/70 font-mono text-sm tracking-widest">AEROSPACE-GRADE DATA SECURITY // ONLINE</p>
            </div>
          </div>

          <div className="flex flex-col items-end gap-1">
             <div className="text-xs font-mono text-hudCyan/50">SYS.STATUS</div>
             <div className="px-4 py-1 border border-hudGreen text-hudGreen bg-hudGreen/10 font-mono text-sm flex items-center gap-2 shadow-[0_0_10px_#00ff88_inset]">
                <span className="w-2 h-2 bg-hudGreen block animate-pulse"></span>
                SECURE
             </div>
          </div>
        </motion.header>

        {/* Global Telemetry Arrays */}
        <motion.div 
          className="grid grid-cols-1 md:grid-cols-4 gap-4"
          initial="initial" animate="animate" variants={{
            animate: { transition: { staggerChildren: 0.05 }}
          }}
        >
          <StatCard title="TOTAL SCANS" value={analytics?.total} icon={<Cpu />} color="text-hudCyan" />
          <StatCard title="CRITICAL BREACH" value={analytics?.severity_distribution.high} icon={<AlertOctagon />} color="text-hudRed" border="border-hudRed" textGlow="glow-text-alert" shadow="shadow-[0_0_15px_rgba(255,42,42,0.2)_inset]" />
          <StatCard title="ACTIVE USERS" value={analytics?.top_users.length} icon={<TerminalSquare />} color="text-hudCyan" />
          <StatCard title="VALIDATED" value={incidents.filter(i => i.github_confirmed).length} icon={<CheckSquare />} color="text-hudCyan" />
        </motion.div>

        {/* Log Viewer (Table) */}
        <motion.div {...snapIn} transition={{ delay: 0.2 }} className="hud-panel p-6 mt-6 flex-1">
          <div className="flex items-center justify-between mb-6">
             <h2 className="text-xl font-bold flex items-center gap-2 text-hudText uppercase tracking-widest">
               <ShieldAlert className="text-hudCyan w-5 h-5"/> Live Threat Stream
             </h2>
             <span className="font-mono text-xs text-hudCyan/50">AUTO-UPDATE: 10s</span>
          </div>
          
          <div className="overflow-x-auto">
            <table className="w-full text-left font-mono text-sm border-collapse">
              <thead>
                <tr className="border-b-2 border-hudCyan/30 text-hudCyan/70">
                  <th className="py-2 px-4 uppercase tracking-widest font-normal">T-MINUS (UTC)</th>
                  <th className="py-2 px-4 uppercase tracking-widest font-normal">ORIGIN ID</th>
                  <th className="py-2 px-4 uppercase tracking-widest font-normal">DIAGNOSTIC REASON</th>
                  <th className="py-2 px-4 uppercase tracking-widest font-normal text-center">RISK LVL</th>
                  <th className="py-2 px-4 uppercase tracking-widest font-normal text-center">VALIDATION</th>
                </tr>
              </thead>
              <tbody>
                <AnimatePresence>
                  {incidents.map((inc) => (
                    <motion.tr 
                      key={inc.id}
                      layout
                      initial={{ opacity: 0, x: -20, backgroundColor: "rgba(0,221,255,0.4)" }}
                      animate={{ opacity: 1, x: 0, backgroundColor: "transparent" }}
                      exit={{ opacity: 0 }}
                      className="border-b border-hudCyan/10 hover:bg-hudCyan/5 transition-colors group cursor-crosshair"
                    >
                      <td className="py-4 px-4 text-hudCyan/60 group-hover:text-hudCyan transition-colors">
                        {new Date(inc.timestamp).toISOString().replace("T", " ").substring(0, 19)}
                      </td>
                      <td className="py-4 px-4 font-bold text-white">{inc.user}</td>
                      <td className="py-4 px-4 text-hudCyan/80 max-w-sm truncate" title={inc.ai_reasoning}>&gt; {inc.ai_reasoning}</td>
                      <td className="py-4 px-4 text-center">
                        <span className={`inline-block px-2 py-0 border ${
                          inc.severity >= 7 ? "bg-hudRed/20 text-hudRed border-hudRed glow-text-alert" :
                          inc.severity >= 4 ? "bg-hudAmber/20 text-hudAmber border-hudAmber shadow-[0_0_5px_#ffb400_inset]" :
                          "bg-hudCyan/10 text-hudCyan border-hudCyan shadow-[0_0_5px_#00ddff_inset]"
                        }`}>
                          LVL_{inc.severity}
                        </span>
                      </td>
                      <td className="py-4 px-4 text-center">
                        {inc.github_confirmed ? (
                           <span className="text-hudCyan border-b border-hudCyan animate-pulse">V-TRUE</span>
                        ) : (
                           <span className="text-hudCyan/30">V-FALSE</span>
                        )}
                      </td>
                    </motion.tr>
                  ))}
                </AnimatePresence>
              </tbody>
            </table>
          </div>
        </motion.div>
      </main>
    </>
  );
}

function StatCard({ title, value, icon, color = "text-hudCyan", border = "border-hudCyan/30", textGlow = "", shadow = "" }: any) {
  return (
    <motion.div variants={snapIn} className={`hud-panel p-5 flex flex-col gap-2 ${border} ${shadow} hud-border-l relative`}>
      <div className="flex justify-between items-center">
        <h3 className="text-hudCyan/50 font-bold text-xs tracking-widest">{title}</h3>
        <span className={`${color} opacity-80 w-5 h-5`}>{icon}</span>
      </div>
      <p className={`text-4xl font-mono font-bold text-white tracking-tighter ${textGlow}`}>{value ?? 0}</p>
      {/* Decorative tech bar at the bottom */}
      <div className="absolute bottom-0 left-0 h-[2px] w-1/3 bg-gradient-to-r from-hudCyan to-transparent"></div>
    </motion.div>
  )
}
