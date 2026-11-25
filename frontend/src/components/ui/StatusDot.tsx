import React from 'react';

interface StatusDotProps {
  status: string;
  size?: 'sm' | 'md' | 'lg';
  pulse?: boolean;
}

export const StatusDot: React.FC<StatusDotProps> = ({
  status,
  size = 'md',
  pulse = false,
}) => {
  const getColor = () => {
    switch (status.toUpperCase()) {
      case 'AVAILABLE':
      case 'CONNECTED':
      case 'CLOSED':
      case 'ACTIVE':
      case 'SUCCESS':
      case 'SAFE':
      case 'RUNNING':
        return 'bg-success';
      case 'RESERVED':
      case 'DIALING':
      case 'RINGING':
      case 'HALF_OPEN':
      case 'DEGRADED':
      case 'THROTTLED':
      case 'PAUSED':
        return 'bg-warning';
      case 'OFFLINE':
      case 'CRASHED':
      case 'OPEN':
      case 'FAILED':
      case 'BLOCKED':
      case 'STOPPED':
        return 'bg-danger';
      case 'WRAP_UP':
      case 'QUEUED':
      case 'INITIATED':
      default:
        return 'bg-accent';
    }
  };

  const sizeClasses = {
    sm: 'w-1.5 h-1.5',
    md: 'w-2 h-2',
    lg: 'w-2.5 h-2.5',
  };

  const colorClass = getColor();

  return (
    <span className="relative inline-flex items-center justify-center">
      {pulse && (
        <span
          className={`absolute inline-flex h-full w-full rounded-full opacity-75 animate-ping ${colorClass}`}
        />
      )}
      <span className={`relative inline-flex rounded-full ${colorClass} ${sizeClasses[size]}`} />
    </span>
  );
};
