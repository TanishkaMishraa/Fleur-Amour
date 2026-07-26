import { cn } from "@/lib/utils";

function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("skeleton rounded-xl", className)} {...props} />;
}

/** Pre-built skeleton for a dashboard stat card */
export function StatCardSkeleton() {
  return (
    <div className="luxury-card p-6 space-y-3">
      <Skeleton className="h-3 w-24" />
      <Skeleton className="h-8 w-16" />
      <Skeleton className="h-2.5 w-32" />
    </div>
  );
}

/** Pre-built skeleton for a product card */
export function ProductCardSkeleton() {
  return (
    <div className="luxury-card overflow-hidden">
      <Skeleton className="aspect-square w-full rounded-none" />
      <div className="p-4 space-y-2">
        <Skeleton className="h-3 w-3/4" />
        <Skeleton className="h-3 w-1/2" />
        <Skeleton className="h-4 w-1/3 mt-3" />
      </div>
    </div>
  );
}

export { Skeleton };
