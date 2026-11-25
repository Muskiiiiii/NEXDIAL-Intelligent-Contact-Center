import React from 'react';

interface BadgeProps {
  children: React.ReactNode;
  variant?: 'accent' | 'success' | 'warning' | 'danger' | 'neutral' | 'outline';
  size?: 'sm' | 'md';
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'neutral',
  size = 'md',
  className = '',
}) => {
  const variantStyles = {
    accent: 'bg-[#7C6CFF1F] text-[#7C6CFF] border border-[#7C6CFF44]',
    success: 'bg-[#20C9971F] text-[#20C997] border border-[#20C99744]',
    warning: 'bg-[#F5B9421F] text-[#F5B942] border border-[#F5B94244]',
    danger: 'bg-[#FF5C701F] text-[#FF5C70] border border-[#FF5C7044]',
    neutral: 'bg-[#1E2C4488] text-[#8B96AA] border border-[#1E2C44]',
    outline: 'bg-transparent text-[#F5F7FF] border border-[#1E2C44]',
  };

  const sizeStyles = {
    sm: 'text-[10px] px-1.5 py-0.5 tracking-wider uppercase font-semibold rounded',
    md: 'text-xs px-2.5 py-1 rounded-md font-medium',
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 ${variantStyles[variant]} ${sizeStyles[size]} ${className}`}
    >
      {children}
    </span>
  );
};
