import React from 'react';

export const LoadingSpinner: React.FC<{ size?: 'sm' | 'md' | 'lg'; text?: string }> = ({
  size = 'md',
  text,
}) => {
  const sizeClasses = {
    sm: 'w-4 h-4 border-2',
    md: 'w-8 h-8 border-3',
    lg: 'w-12 h-12 border-4',
  }[size];

  return (
    <div className="flex flex-col items-center justify-center p-6 gap-3 text-slate-400">
      <div
        className={`${sizeClasses} rounded-full border-slate-700 border-t-brand-500 animate-spin`}
      />
      {text && <span className="text-xs font-medium tracking-wide">{text}</span>}
    </div>
  );
};
