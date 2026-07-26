"use client";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { motion } from "framer-motion";
import { Save, Check } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { usersApi } from "@/lib/api/users";
import { useAuthStore } from "@/lib/stores/auth.store";

const schema = z.object({
  full_name: z.string().min(2, "Name must be at least 2 characters").max(100),
});
type FormData = z.infer<typeof schema>;

export function ProfileForm() {
  const { user, patchUser }  = useAuthStore();
  const [saved, setSaved]    = useState(false);

  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { full_name: user?.full_name ?? "" },
  });

  const onSubmit = async (data: FormData) => {
    try {
      const res = await usersApi.updateMe(data);
      if (res.data.success && res.data.data) {
        patchUser(res.data.data);
        setSaved(true);
        setTimeout(() => setSaved(false), 3000);
      }
    } catch {}
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
      <Input
        label="Full name"
        {...register("full_name")}
        error={errors.full_name?.message}
        placeholder="Your full name"
      />

      <div className="space-y-1.5">
        <label className="block text-xs font-medium tracking-wide text-muted-foreground/80">
          Email address
        </label>
        <div className="input-luxury flex items-center opacity-60 cursor-not-allowed select-none">
          {user?.email}
          {user?.is_verified && (
            <span className="ml-auto flex items-center gap-1 text-emerald-400 text-xs">
              <Check className="h-3 w-3" /> Verified
            </span>
          )}
        </div>
        <p className="text-2xs text-muted-foreground/40">Email cannot be changed from this screen.</p>
      </div>

      <Button type="submit" variant="gold" loading={isSubmitting} className="flex items-center gap-2">
        {saved ? (
          <><Check className="h-4 w-4" /> Saved</>
        ) : (
          <><Save className="h-4 w-4" /> Save Changes</>
        )}
      </Button>
    </form>
  );
}
