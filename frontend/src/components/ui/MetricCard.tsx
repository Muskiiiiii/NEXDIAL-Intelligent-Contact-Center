import React from 'react';
import { LucideIcon } from 'lucide-react';

interface MetricCardProps {
  label: string;
  value: string | number;
  subtext?: string;
  icon?: LucideIcon;
  trend?: {
    value: string;
    isPositive?: boolean;
  };
  accentColor?: string; // hex or tailwind class
}

export const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  subtext,
  icon: Icon,
  trend,
  accentColor = '#7C6CFF',
}) => {
  return (
    <div className="bg-card border border-card-border rounded-xl p-4 relative overflow-hidden transition-all duration-200 hover:border-[#2C3E5F]">
      <div
        className="absolute top-0 left-0 right-0 h-[2px] opacity-75"
        style={{ backgroundColor: accentColor }}
      />
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-text-muted uppercase tracking-wider">{label}</span>
        {Icon && (
          <div
            className="w-8 h-8 rounded-lg flex items-center justify-center"
            style={{ backgroundColor: `${accentColor}18`, color: accentColor }}
          >
            <Icon size={16} />
          </div>
        )}
      </div>
      <div className="mt-2.5 flex items-baseline gap-2">
        <span className="text-2xl font-bold text-text tracking-tight">{value}</span>
        {trend && (
          <span
            className={`text-xs font-semibold ${
              trend.isPositive ? 'text-success' : 'text-danger'
            }`}
          >
            {trend.value}
          </span>
        )}
      </div>
      {subtext && <p className="text-[11px] text-text-subtle mt-1">{subtext}</p>}
    </div>
  );
};
