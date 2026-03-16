import * as React from 'react';
import { cn } from '@/lib/utils';

export interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'text' | 'circle' | 'rect';
  width?: string;
  height?: string;
}

const Skeleton = React.forwardRef<HTMLDivElement, SkeletonProps>(
  ({ className, variant = 'text', width, height, style, ...props }, ref) => {
    const variants = {
      text: 'h-4 rounded-md',
      circle: 'rounded-full',
      rect: 'rounded-xl',
    };

    return (
      <div
        ref={ref}
        className={cn(
          'bg-stone-200/60 animate-shimmer',
          variants[variant],
          className
        )}
        style={{ width, height, ...style }}
        {...props}
      />
    );
  }
);

Skeleton.displayName = 'Skeleton';

export { Skeleton };
