"use client";
import { motion } from "framer-motion";
import { Smartphone, Monitor, Tablet, MapPin, Clock, Trash2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { UserSession } from "@/types";

function DeviceIcon({ type }: { type: string | null }) {
  if (type === "mobile")  return <Smartphone className="h-4 w-4" />;
  if (type === "tablet")  return <Tablet className="h-4 w-4" />;
  return <Monitor className="h-4 w-4" />;
}

function timeAgo(dateStr: string | null): string {
  if (!dateStr) return "Unknown";
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins  = Math.floor(diff / 60000);
  if (mins < 1)   return "Just now";
  if (mins < 60)  return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24)   return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

interface SessionCardProps {
  session:   UserSession;
  onRevoke:  (id: string) => void;
  revoking?: boolean;
}

export function SessionCard({ session, onRevoke, revoking }: SessionCardProps) {
  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, x: -20 }}
      className="flex items-center gap-4 rounded-xl border border-white/[0.06] bg-white/[0.02] p-4"
    >
      {/* Device icon */}
      <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border ${
        session.is_current
          ? "border-brand-gold/30 bg-brand-gold/10 text-brand-gold"
          : "border-white/[0.06] bg-white/[0.03] text-muted-foreground/50"
      }`}>
        <DeviceIcon type={session.device_type} />
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0 space-y-1">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm font-medium text-foreground truncate">
            {session.device_name ?? session.device_type ?? "Unknown device"}
          </span>
          {session.is_current && (
            <Badge variant="gold" className="text-2xs">
              <span className="h-1.5 w-1.5 rounded-full bg-brand-gold animate-pulse" />
              Current
            </Badge>
          )}
        </div>
        <div className="flex items-center gap-4 text-xs text-muted-foreground/50 flex-wrap">
          {session.ip_address && (
            <span className="flex items-center gap-1">
              <MapPin className="h-3 w-3" />
              {session.ip_address}
              {session.location && ` · ${session.location}`}
            </span>
          )}
          <span className="flex items-center gap-1">
            <Clock className="h-3 w-3" />
            Active {timeAgo(session.last_active_at)}
          </span>
        </div>
      </div>

      {/* Revoke */}
      {!session.is_current && (
        <button
          onClick={() => onRevoke(session.id)}
          disabled={revoking}
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-muted-foreground/40 hover:text-destructive hover:bg-destructive/10 transition-all disabled:opacity-40"
          title="Revoke session"
        >
          {revoking
            ? <span className="h-3.5 w-3.5 rounded-full border-2 border-current border-t-transparent animate-spin" />
            : <Trash2 className="h-3.5 w-3.5" />
          }
        </button>
      )}
    </motion.div>
  );
}
