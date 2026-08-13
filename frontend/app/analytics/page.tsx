"use client";

import { useEffect, useState } from "react";
import { Activity, CheckCircle, XCircle, Phone } from "lucide-react";
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend
} from "recharts";

type CallRecord = {
  id: number;
  contact: string;
  name: string;
  outcome: string;
  detail: string;
  created_at: string;
};

type DailyActivity = {
  date: string;
  total: number;
  successful: number;
  failed: number;
};

type AnalyticsData = {
  total_calls: number;
  successful_calls: number;
  failed_calls: number;
  recent_calls: CallRecord[];
  daily_activity: DailyActivity[];
};

export default function AnalyticsDashboard() {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchAnalytics() {
      try {
        const res = await fetch("/api/analytics");
        const json = await res.json();
        setData(json);
      } catch (err) {
        console.error("Failed to fetch analytics:", err);
      } finally {
        setLoading(false);
      }
    }
    fetchAnalytics();
    
    // Auto-refresh every 5 seconds
    const interval = setInterval(fetchAnalytics, 5000);
    return () => clearInterval(interval);
  }, []);

  const pieData = data ? [
    { name: "Successful", value: data.successful_calls },
    { name: "Failed", value: data.failed_calls },
  ] : [];

  const COLORS = ["#10b981", "#f43f5e"]; // Emerald and Rose

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-white p-8 font-sans selection:bg-blue-500/30">
      <div className="max-w-7xl mx-auto space-y-10">
        
        {/* Header */}
        <header className="flex flex-col md:flex-row md:items-end justify-between border-b border-white/10 pb-6 gap-4">
          <div>
            <h1 className="text-4xl font-extrabold tracking-tight bg-gradient-to-r from-blue-400 to-indigo-600 bg-clip-text text-transparent">
              Analytics Dashboard
            </h1>
            <p className="text-zinc-400 mt-2">
              Deep insights into Vidya Vani's learning sessions and outcomes.
            </p>
          </div>
          <div className="flex items-center gap-3 bg-white/5 px-4 py-2 rounded-full border border-white/10">
            <span className="relative flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
            </span>
            <span className="text-sm font-medium text-emerald-400">Live Data Active</span>
          </div>
        </header>

        {loading && !data ? (
          <div className="flex items-center justify-center py-32">
            <div className="w-10 h-10 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
          </div>
        ) : (
          <>
            {/* Top Metric Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="group relative overflow-hidden rounded-3xl bg-white/5 border border-white/10 backdrop-blur-md p-8 transition-all hover:bg-white/10">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-medium text-zinc-300">Total Calls</h3>
                  <div className="p-3 bg-blue-500/10 rounded-xl">
                    <Activity className="w-6 h-6 text-blue-400" />
                  </div>
                </div>
                <p className="text-5xl font-bold text-white">{data?.total_calls || 0}</p>
              </div>

              <div className="group relative overflow-hidden rounded-3xl bg-white/5 border border-white/10 backdrop-blur-md p-8 transition-all hover:bg-white/10">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-medium text-zinc-300">Successful Calls</h3>
                  <div className="p-3 bg-emerald-500/10 rounded-xl">
                    <CheckCircle className="w-6 h-6 text-emerald-400" />
                  </div>
                </div>
                <p className="text-5xl font-bold text-white">{data?.successful_calls || 0}</p>
              </div>

              <div className="group relative overflow-hidden rounded-3xl bg-white/5 border border-white/10 backdrop-blur-md p-8 transition-all hover:bg-white/10">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-medium text-zinc-300">Failed Calls</h3>
                  <div className="p-3 bg-rose-500/10 rounded-xl">
                    <XCircle className="w-6 h-6 text-rose-400" />
                  </div>
                </div>
                <p className="text-5xl font-bold text-white">{data?.failed_calls || 0}</p>
              </div>
            </div>

            {/* Charts Section */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              
              {/* Daily Activity Bar Chart */}
              <div className="lg:col-span-2 rounded-3xl bg-white/5 border border-white/10 p-8">
                <h3 className="text-xl font-bold mb-6 text-white">Call Volume Trend</h3>
                <div className="h-[300px] w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={data?.daily_activity || []} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                      <XAxis dataKey="date" stroke="#71717a" fontSize={12} tickLine={false} axisLine={false} />
                      <YAxis stroke="#71717a" fontSize={12} tickLine={false} axisLine={false} />
                      <Tooltip 
                        cursor={{fill: 'rgba(255, 255, 255, 0.05)'}}
                        contentStyle={{ backgroundColor: '#18181b', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px' }}
                      />
                      <Legend iconType="circle" />
                      <Bar dataKey="successful" name="Successful" stackId="a" fill="#10b981" radius={[0, 0, 4, 4]} />
                      <Bar dataKey="failed" name="Failed" stackId="a" fill="#f43f5e" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Success Distribution Donut Chart */}
              <div className="rounded-3xl bg-white/5 border border-white/10 p-8 flex flex-col">
                <h3 className="text-xl font-bold mb-2 text-white">Success Rate</h3>
                <p className="text-zinc-400 text-sm mb-6">Distribution of call outcomes</p>
                <div className="flex-1 h-[250px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={pieData}
                        cx="50%"
                        cy="50%"
                        innerRadius={70}
                        outerRadius={90}
                        paddingAngle={5}
                        dataKey="value"
                        stroke="none"
                      >
                        {pieData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip 
                        contentStyle={{ backgroundColor: '#18181b', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px' }}
                        itemStyle={{ color: '#fff' }}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>

            {/* Recent Calls Data Table */}
            <div className="rounded-3xl bg-white/5 border border-white/10 overflow-hidden">
              <div className="p-6 border-b border-white/10 bg-white/[0.02]">
                <h3 className="text-xl font-bold text-white flex items-center gap-2">
                  <Phone className="w-5 h-5 text-blue-400" />
                  Recent Call Logs
                </h3>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm text-zinc-300">
                  <thead className="bg-white/[0.02] text-xs uppercase text-zinc-400 border-b border-white/10">
                    <tr>
                      <th className="px-6 py-4 font-medium">Date & Time</th>
                      <th className="px-6 py-4 font-medium">Learner Name</th>
                      <th className="px-6 py-4 font-medium">Room / Contact</th>
                      <th className="px-6 py-4 font-medium">Outcome</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {data?.recent_calls?.length === 0 ? (
                      <tr>
                        <td colSpan={4} className="px-6 py-8 text-center text-zinc-500">No calls recorded yet.</td>
                      </tr>
                    ) : (
                      data?.recent_calls?.map((call) => (
                        <tr key={call.id} className="hover:bg-white/[0.02] transition-colors">
                          <td className="px-6 py-4 whitespace-nowrap">
                            {new Date(call.created_at).toLocaleString()}
                          </td>
                          <td className="px-6 py-4 font-medium text-white">{call.name}</td>
                          <td className="px-6 py-4 text-zinc-400">{call.contact}</td>
                          <td className="px-6 py-4">
                            {call.outcome === "Successful" ? (
                              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                                Successful
                              </span>
                            ) : (
                              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-rose-500/10 text-rose-400 border border-rose-500/20">
                                Failed
                              </span>
                            )}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>

          </>
        )}
      </div>
    </div>
  );
}
