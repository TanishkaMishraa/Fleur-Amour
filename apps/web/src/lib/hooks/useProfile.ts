/**
 * AuraFit — useProfile hook.
 * React Query wrapper for the beauty/style profile.
 * Syncs updates to auth store for global availability.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { profileApi } from "@/lib/api/users";
import { useAuthStore } from "@/lib/stores/auth.store";
import type { UserProfile } from "@/types";

export function useProfile() {
  const qc    = useQueryClient();
  const store = useAuthStore();

  const query = useQuery({
    queryKey: ["profile"],
    queryFn: async () => {
      const { data } = await profileApi.getProfile();
      const profile  = data.data as UserProfile;
      store.setProfile(profile);
      return profile;
    },
    initialData: store.profile ?? undefined,
    staleTime:   1000 * 60 * 5,   // 5 min
  });

  const update = useMutation({
    mutationFn: (data: Partial<UserProfile>) => profileApi.updateProfile(data),
    onSuccess: (res) => {
      if (res.data.success && res.data.data) {
        store.setProfile(res.data.data);
        qc.invalidateQueries({ queryKey: ["profile"] });
      }
    },
  });

  return {
    profile:   query.data,
    isLoading: query.isLoading,
    update:    update.mutateAsync,
    isUpdating: update.isPending,
    error:     update.error,
  };
}
