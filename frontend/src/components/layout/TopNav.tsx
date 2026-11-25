import React, { useState, useEffect } from 'react';
import {
  Bell,
  Clock,
  ShieldCheck,
  Activity,
  User,
  Radio,
  CheckCircle2,
  AlertTriangle,
  X,
} from 'lucide-react';
import { useWebSocketStatus, useWebSocketEvent } from '../../services/websocket';
import { Badge } from '../ui/Badge';

interface TopNavProps {
  isSidebarCollapsed: boolean;
}

export const TopNav: React.FC<TopNavProps> = ({ isSidebarCollapsed }) => {
  const isConnected = useWebSocketStatus();
  const [time, setTime] = useState<string>('');
  const [showNotifications, setShowNotifications] = useState(false);
  const [notifications, setNotifications] = useState<Array<{ id: string; title: string; time: string; type: string }>>([
    { id: '1', title: 'System initialized in SIMULATION mode', time: 'Just now', type: 'info' },
    { id: '2', title: 'Safety Controller armed with zero-abandonment policy', time: '1m ago', type: 'success' },
  ]);

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setTime(now.toLocaleTimeString('en-US', { hour12: false }));
    };
    updateTime();
    const timer = setInterval(updateTime, 1000);
    return () => clearInterval(timer);
  }, []);

  useWebSocketEvent('SAFETY_DECISION', (data: any) => {
    setNotifications((prev) => [
      {
        id: Math.random().toString(),
        title: `Safety: ${data.decision} (${data.approved_calls} approved, ${data.rejected_calls} rejected)`,
        time: 'Just now',
        type: data.decision === 'APPROVE' ? 'success' : 'warning',
      },
      ...prev.slice(0, 10),
    ]);
  });

  return (
    <header
      className={`fixed top-0 right-0 z-20 h-16 bg-background-secondary/80 backdrop-blur-md border-b border-card-border px-6 flex items-center justify-between transition-all duration-300 ${
        isSidebarCollapsed ? 'left-16' : 'left-64'
      }`}
    >
      {/* Left: Environment & Safety Indicators */}
      <div className="flex items-center gap-3">
        <Badge variant="accent" size="sm" className="font-mono">
          <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse" />
          ENVIRONMENT: SIMULATION
        </Badge>

        <div className="hidden sm:flex items-center gap-2 px-2.5 py-1 rounded-md bg-[#151F30] border border-card-border text-xs text-text-muted">
          <ShieldCheck size={14} className="text-success" />
          <span>Safety Controller:</span>
          <span className="text-success font-semibold">STRICT ENFORCEMENT</span>
        </div>
      </div>

      {/* Right: Live Telemetry, Notifications, Profile */}
      <div className="flex items-center gap-4">
        {/* WebSocket Health Dot */}
        <div className="flex items-center gap-2 text-xs text-text-muted bg-[#151F30] px-3 py-1.5 rounded-lg border border-card-border">
          <span
            className={`w-2 h-2 rounded-full ${
              isConnected ? 'bg-success animate-pulse' : 'bg-danger'
            }`}
          />
          <span className="hidden md:inline font-mono">
            {isConnected ? 'LIVE WEBSOCKET' : 'CONNECTING...'}
          </span>
        </div>

        {/* Live Clock */}
        <div className="hidden lg:flex items-center gap-1.5 text-xs text-text-muted font-mono bg-[#151F30] px-3 py-1.5 rounded-lg border border-card-border">
          <Clock size={13} className="text-accent" />
          <span>{time} UTC</span>
        </div>

        {/* Notifications Bell */}
        <div className="relative">
          <button
            onClick={() => setShowNotifications(!showNotifications)}
            className="relative text-text-muted hover:text-text p-2 rounded-lg hover:bg-card border border-transparent hover:border-card-border transition-colors"
          >
            <Bell size={16} />
            {notifications.length > 0 && (
              <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-accent rounded-full animate-ping" />
            )}
          </button>

          {/* Notifications Dropdown */}
          {showNotifications && (
            <div className="absolute right-0 mt-2 w-80 bg-card border border-card-border rounded-xl shadow-2xl p-3 z-50 animate-in fade-in zoom-in-95 duration-150">
              <div className="flex items-center justify-between pb-2 mb-2 border-b border-card-border">
                <span className="text-xs font-semibold text-text">Live Events</span>
                <button
                  onClick={() => setShowNotifications(false)}
                  className="text-text-muted hover:text-text"
                >
                  <X size={14} />
                </button>
              </div>
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {notifications.map((n) => (
                  <div
                    key={n.id}
                    className="p-2 rounded-lg bg-[#101827] border border-card-border text-xs flex flex-col gap-0.5"
                  >
                    <div className="flex items-center gap-1.5">
                      {n.type === 'success' ? (
                        <CheckCircle2 size={12} className="text-success" />
                      ) : (
                        <AlertTriangle size={12} className="text-warning" />
                      )}
                      <span className="font-medium text-text text-[11px] truncate">{n.title}</span>
                    </div>
                    <span className="text-[10px] text-text-subtle self-end">{n.time}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* User Profile */}
        <div className="flex items-center gap-2.5 pl-2 border-l border-card-border">
          <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-[#7C6CFF44] to-[#20C99744] border border-[#7C6CFF66] flex items-center justify-center text-text font-bold text-xs">
            OP
          </div>
          <div className="hidden xl:flex flex-col">
            <span className="text-xs font-semibold text-text leading-tight">Admin Console</span>
            <span className="text-[10px] text-text-muted leading-tight">Supervisor</span>
          </div>
        </div>
      </div>
    </header>
  );
};
