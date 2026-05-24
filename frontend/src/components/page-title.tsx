import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

export interface PageTitleProps {
  eyebrow?: string;
  title: string;
  description?: string;
  actions?: ReactNode;
  className?: string;
}

export function PageTitle({
  eyebrow,
  title,
  description,
  actions,
  className,
}: PageTitleProps) {
  return (
    <div className={cn("flex items-start justify-between mb-6", className)}>
      <div className="space-y-0.5">
        {eyebrow && (
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
            {eyebrow}
          </p>
        )}
        <h1 className="text-2xl font-bold text-foreground">{title}</h1>
        {description && (
          <p className="text-sm text-muted-foreground">{description}</p>
        )}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}
