import React from 'react';
import {
  LayoutDashboard,
  Radio,
  Layers,
  Users,
  ListOrdered,
  PhoneCall,
  BrainCircuit,
  ShieldCheck,
  Server,
  FlaskConical,
  ZapOff,
  BarChart3,
  Network,
  Settings as SettingsIcon,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';

interface SidebarProps {
  currentTab: string;
  onSelectTab: (tab: string) => void;
  isCollapsed: boolean;
  onToggleCollapse: () => void;
}

export const navItems = [
  { id: 'overview', label: 'Overview', icon: LayoutDashboard },
  { id: 'live-operations', label: 'Live Operations', icon: Radio, badge: 'LIVE' },
  { id: 'campaigns', label: 'Campaigns', icon: Layers },
  { id: 'agents', label: 'Agent Management', icon: Users },
  { id: 'borrowers', label: 'Borrower Queue', icon: ListOrdered },
  { id: 'calls', label: 'Call History', icon: PhoneCall },
  { id: 'predictive', label: 'Predictive Engine', icon: BrainCircuit },
  { id: 'safety', label: 'Safety Controller', icon: ShieldCheck, highlight: true },
  { id: 'providers', label: 'Provider Health', icon: Server },
  { id: 'simulation', label: 'Simulation Lab', icon: FlaskConical, badge: 'LAB' },
  { id: 'failures', label: 'Failure Injection', icon: ZapOff },
  { id: 'analytics', label: 'Analytics', icon: BarChart3 },
  { id: 'architecture', label: 'System Architecture', icon: Network },
  { id: 'settings', label: 'Settings', icon: SettingsIcon },
];

export const Sidebar: React.FC<SidebarProps> = ({
  currentTab,
  onSelectTab,
  isCollapsed,
  onToggleCollapse,
}) => {
  return (
    <aside
      className={`fixed top-0 bottom-0 left-0 z-30 bg-background-secondary border-r border-card-border transition-all duration-300 flex flex-col ${
        isCollapsed ? 'w-16' : 'w-64'
      }`}
    >
      {/* Brand Header */}
      <div className="h-16 flex items-center justify-between px-4 border-b border-card-border">
        {!isCollapsed && (
          <div className="flex items-center gap-2.5 overflow-hidden">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-[#7C6CFF] to-[#9B8CFF] flex items-center justify-center text-white shadow-glow-accent flex-shrink-0">
              <Radio size={18} className="animate-pulse" />
            </div>
            <div className="flex flex-col">
              <span className="font-extrabold text-sm tracking-wider text-text flex items-center gap-1.5">
                NEXDIAL
                <span className="text-[10px] bg-[#7C6CFF22] text-accent px-1.5 py-0.2 rounded font-semibold border border-[#7C6CFF44]">
                  v1.0
                </span>
              </span>
              <span className="text-[10px] text-text-muted font-medium tracking-tight truncate">
                Intelligent Contact Center
              </span>
            </div>
          </div>
        )}
        {isCollapsed && (
          <div className="w-8 h-8 mx-auto rounded-lg bg-gradient-to-tr from-[#7C6CFF] to-[#9B8CFF] flex items-center justify-center text-white shadow-glow-accent">
            <Radio size={18} />
          </div>
        )}
        <button
          onClick={onToggleCollapse}
          className="text-text-muted hover:text-text p-1.5 rounded-lg hover:bg-card transition-colors hidden md:block"
          title={isCollapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}
        >
          {isCollapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
        </button>
      </div>

      {/* Navigation Items */}
      <div className="flex-1 overflow-y-auto py-3 px-2 space-y-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onSelectTab(item.id)}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-medium transition-all group relative ${
                isActive
                  ? 'bg-accent text-white shadow-glow-accent font-semibold'
                  : 'text-text-muted hover:text-text hover:bg-card'
              }`}
              title={isCollapsed ? item.label : undefined}
            >
              <Icon
                size={16}
                className={`flex-shrink-0 ${
                  isActive ? 'text-white' : item.highlight ? 'text-accent' : 'text-text-muted group-hover:text-text'
                }`}
              />
              {!isCollapsed && (
                <div className="flex-1 flex items-center justify-between text-left truncate">
                  <span className="truncate">{item.label}</span>
                  {item.badge && (
                    <span
                      className={`text-[9px] px-1.5 py-0.2 rounded font-mono font-bold tracking-wider ${
                        isActive
                          ? 'bg-white/20 text-white'
                          : 'bg-[#7C6CFF22] text-accent border border-[#7C6CFF44]'
                      }`}
                    >
                      {item.badge}
                    </span>
                  )}
                </div>
              )}
            </button>
          );
        })}
      </div>

      {/* Safety & System Status Footer */}
      {!isCollapsed && (
        <div className="p-3 border-t border-card-border bg-[#090D1888]">
          <div className="flex items-center justify-between text-[11px] text-text-muted mb-1">
            <span className="flex items-center gap-1.5 font-medium">
              <span className="w-2 h-2 rounded-full bg-success animate-pulse" />
              Safety Controller
            </span>
            <span className="text-success font-semibold">ACTIVE</span>
          </div>
          <div className="w-full bg-[#1E2C44] h-1.5 rounded-full overflow-hidden">
            <div className="bg-success h-full w-[100%] rounded-full" />
          </div>
          <div className="flex justify-between text-[10px] text-text-subtle mt-1.5">
            <span>Pacing Guard: 100%</span>
            <span>Zero Abandonment</span>
          </div>
        </div>
      )}
    </aside>
  );
};
