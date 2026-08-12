"use client";

import { useEffect, useState } from "react";

type Ticket = {
  ticket_id: string;
  customer_name: string;
  issue_summary: string;
  urgency: string;
  created_at: string;
};

export default function TicketsDashboard() {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchTickets() {
      try {
        const res = await fetch("/api/tickets");
        const data = await res.json();
        if (data.tickets) {
          setTickets(data.tickets);
        }
      } catch (err) {
        console.error("Failed to fetch tickets:", err);
      } finally {
        setLoading(false);
      }
    }
    fetchTickets();
  }, []);

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-white p-8 font-sans selection:bg-purple-500/30">
      <div className="max-w-6xl mx-auto space-y-8">
        <header className="flex flex-col md:flex-row md:items-end justify-between border-b border-white/10 pb-6 gap-4">
          <div>
            <h1 className="text-4xl font-extrabold tracking-tight bg-gradient-to-r from-purple-400 to-pink-600 bg-clip-text text-transparent">
              Escalation Dashboard
            </h1>
            <p className="text-zinc-400 mt-2">
              Review and manage human assistance requests from the Vidya Vani agent.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <span className="relative flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
            </span>
            <span className="text-sm font-medium text-zinc-300">
              {tickets.length} Active Tickets
            </span>
          </div>
        </header>

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="w-8 h-8 border-4 border-purple-500 border-t-transparent rounded-full animate-spin"></div>
          </div>
        ) : tickets.length === 0 ? (
          <div className="text-center py-20 border border-white/5 rounded-2xl bg-white/5 backdrop-blur-xl">
            <h3 className="text-xl font-medium text-zinc-200 mb-2">All caught up!</h3>
            <p className="text-zinc-500">No human escalation tickets have been issued yet.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {tickets.map((ticket) => (
              <div 
                key={ticket.ticket_id} 
                className="group relative overflow-hidden rounded-2xl bg-white/5 border border-white/10 backdrop-blur-md p-6 hover:bg-white/10 transition-all duration-300 hover:-translate-y-1 hover:shadow-2xl hover:shadow-purple-500/10"
              >
                <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-purple-500 to-pink-500 opacity-0 group-hover:opacity-100 transition-opacity"></div>
                
                <div className="flex justify-between items-start mb-4">
                  <span className="px-3 py-1 bg-white/10 rounded-full text-xs font-mono text-purple-300 font-semibold tracking-wide border border-purple-500/30">
                    {ticket.ticket_id}
                  </span>
                  
                  {ticket.urgency.toLowerCase() === 'high' ? (
                    <span className="flex items-center gap-1 text-xs font-semibold text-rose-400 bg-rose-500/10 px-2 py-1 rounded-md border border-rose-500/20">
                      <span className="w-1.5 h-1.5 rounded-full bg-rose-500 animate-pulse"></span>
                      High
                    </span>
                  ) : ticket.urgency.toLowerCase() === 'medium' ? (
                    <span className="text-xs font-semibold text-amber-400 bg-amber-500/10 px-2 py-1 rounded-md border border-amber-500/20">
                      Medium
                    </span>
                  ) : (
                    <span className="text-xs font-semibold text-emerald-400 bg-emerald-500/10 px-2 py-1 rounded-md border border-emerald-500/20">
                      Low
                    </span>
                  )}
                </div>

                <div className="space-y-3">
                  <div>
                    <h3 className="text-lg font-semibold text-zinc-100 flex items-center gap-2">
                      {ticket.customer_name}
                    </h3>
                  </div>
                  
                  <div className="bg-black/20 rounded-lg p-3 border border-white/5">
                    <p className="text-sm text-zinc-300 leading-relaxed line-clamp-3">
                      {ticket.issue_summary}
                    </p>
                  </div>
                </div>

                <div className="mt-6 pt-4 border-t border-white/5 flex items-center justify-between text-xs text-zinc-500">
                  <span>
                    {new Intl.DateTimeFormat('en-US', { 
                      month: 'short', day: 'numeric', year: 'numeric', 
                      hour: 'numeric', minute: '2-digit', hour12: true 
                    }).format(new Date(ticket.created_at))}
                  </span>
                  <button className="text-purple-400 hover:text-purple-300 font-medium transition-colors">
                    Resolve
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
