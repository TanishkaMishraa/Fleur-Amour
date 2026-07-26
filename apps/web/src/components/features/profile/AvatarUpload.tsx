"use client";
import { useRef, useState } from "react";
import { motion } from "framer-motion";
import { Camera, Trash2 } from "lucide-react";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { usersApi } from "@/lib/api/users";
import { useAuthStore } from "@/lib/stores/auth.store";
import { getInitials } from "@/lib/utils";

export function AvatarUpload() {
  const { user, patchUser }   = useAuthStore();
  const fileRef               = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError]     = useState("");

  const handleFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (file.size > 5 * 1024 * 1024) {
      setError("Image must be under 5 MB"); return;
    }
    if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)) {
      setError("JPG, PNG, or WebP only"); return;
    }

    setUploading(true); setError("");
    try {
      const { data } = await usersApi.uploadAvatar(file);
      if (data.success && data.data) {
        patchUser({ avatar_url: data.data.avatar_url });
      }
    } catch { setError("Upload failed. Try again."); }
    finally { setUploading(false); }
  };

  const removeAvatar = async () => {
    setUploading(true);
    try {
      await usersApi.removeAvatar();
      patchUser({ avatar_url: null });
    } catch { setError("Failed to remove avatar."); }
    finally { setUploading(false); }
  };

  return (
    <div className="flex items-center gap-5">
      <div className="relative">
        <Avatar className="h-20 w-20 ring-2 ring-brand-gold/20">
          <AvatarImage src={user?.avatar_url ?? undefined} />
          <AvatarFallback className="text-lg">
            {user?.full_name ? getInitials(user.full_name) : "AF"}
          </AvatarFallback>
        </Avatar>
        {uploading && (
          <div className="absolute inset-0 flex items-center justify-center rounded-full bg-black/60">
            <span className="h-5 w-5 rounded-full border-2 border-white/30 border-t-white animate-spin" />
          </div>
        )}
        <motion.button
          whileHover={{ scale: 1.1 }}
          onClick={() => fileRef.current?.click()}
          disabled={uploading}
          className="absolute -bottom-1 -right-1 flex h-7 w-7 items-center justify-center rounded-full bg-brand-gold shadow-gold-sm border-2 border-background"
          title="Change photo"
        >
          <Camera className="h-3.5 w-3.5 text-brand-black" />
        </motion.button>
      </div>

      <div className="space-y-1.5">
        <button
          onClick={() => fileRef.current?.click()}
          disabled={uploading}
          className="text-sm font-medium text-brand-gold hover:text-brand-gold-light transition-colors"
        >
          Change photo
        </button>
        {user?.avatar_url && (
          <button
            onClick={removeAvatar}
            disabled={uploading}
            className="flex items-center gap-1 text-xs text-muted-foreground/50 hover:text-destructive transition-colors"
          >
            <Trash2 className="h-3 w-3" /> Remove
          </button>
        )}
        <p className="text-2xs text-muted-foreground/40">JPG, PNG, WebP · Max 5 MB</p>
        {error && <p className="text-xs text-destructive">{error}</p>}
      </div>

      <input
        ref={fileRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        className="hidden"
        onChange={handleFile}
      />
    </div>
  );
}
