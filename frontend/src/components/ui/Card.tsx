import React from 'react';

interface CardProps {
  children: React.ReactNode;
  title?: React.ReactNode;
  subtitle?: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
  headerClassName?: string;
  contentClassName?: string;
}

export const Card: React.FC<CardProps> = ({
  children,
  title,
  subtitle,
  action,
  className = '',
  headerClassName = '',
  contentClassName = '',
}) => {
  return (
    <div className={`bg-card border border-card-border rounded-xl shadow-card-subtle overflow-hidden ${className}`}>
      {(title || action) && (
        <div className={`px-5 py-4 border-b border-card-border flex items-center justify-between ${headerClassName}`}>
          <div>
            {typeof title === 'string' ? (
              <h3 className="text-sm font-semibold text-text tracking-tight">{title}</h3>
            ) : (
              title
            )}
            {subtitle && <p className="text-xs text-text-muted mt-0.5">{subtitle}</p>}
          </div>
          {action && <div className="flex items-center gap-2">{action}</div>}
        </div>
      )}
      <div className={`p-5 ${contentClassName}`}>{children}</div>
    </div>
  );
};
