/**
 * AuraFit — useSessions hook.
 * Manages device session list with React Query.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { sessionsApi } from "@/lib/api/users";
import type { UserSession } from "@/types";

export function useSessions() {
  const qc = useQueryClient();

  const query = useQuery({
    queryKey: ["sessions"],
    queryFn: async () => {
      const { data } = await sessionsApi.listSessions();
      return (data.data ?? []) as UserSession[];
    },
  });

  const revokeOne = useMutation({
    mutationFn: (sessionId: string) => sessionsApi.revokeSession(sessionId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["sessions"] }),
  });

  const revokeOthers = useMutation({
    mutationFn: () => sessionsApi.revokeAllOtherSessions(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["sessions"] }),
  });

  return {
    sessions:     query.data ?? [],
    isLoading:    query.isLoading,
    revokeOne:    revokeOne.mutateAsync,
    revokeOthers: revokeOthers.mutateAsync,
    isRevoking:   revokeOne.isPending || revokeOthers.isPending,
  };
}
