/**
 * AuraFit — usePreferences hook.
 * React Query wrapper for user preferences with optimistic updates.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { preferencesApi } from "@/lib/api/users";
import { useAuthStore } from "@/lib/stores/auth.store";
import type { UserPreferences } from "@/types";

export function usePreferences() {
  const qc      = useQueryClient();
  const store   = useAuthStore();

  const query = useQuery({
    queryKey: ["preferences"],
    queryFn:  async () => {
      const { data } = await preferencesApi.getPreferences();
      const prefs = data.data as UserPreferences;
      store.setPreferences(prefs);
      return prefs;
    },
    initialData: store.preferences ?? undefined,
  });

  const update = useMutation({
    mutationFn: (data: Partial<UserPreferences>) =>
      preferencesApi.updatePreferences(data),
    onSuccess: (res) => {
      if (res.data.success && res.data.data) {
        store.setPreferences(res.data.data);
        qc.invalidateQueries({ queryKey: ["preferences"] });
      }
    },
  });

  return {
    preferences: query.data,
    isLoading:   query.isLoading,
    update:      update.mutateAsync,
    isUpdating:  update.isPending,
  };
}
