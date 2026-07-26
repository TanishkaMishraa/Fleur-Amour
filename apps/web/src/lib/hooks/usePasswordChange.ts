/**
 * AuraFit — usePasswordChange hook.
 * Wraps the change-password API call with loading + error state.
 * Distinct from the password-reset flow (requires current password).
 */
import { useState, useCallback } from "react";
import { authExtendedApi } from "@/lib/api/users";

interface ChangePasswordResult {
  success: boolean;
  error?:  string;
}

export function usePasswordChange() {
  const [isLoading, setIsLoading] = useState(false);
  const [error,     setError]     = useState<string | null>(null);
  const [success,   setSuccess]   = useState(false);

  const changePassword = useCallback(
    async (currentPassword: string, newPassword: string): Promise<ChangePasswordResult> => {
      setIsLoading(true);
      setError(null);
      setSuccess(false);
      try {
        const { data } = await authExtendedApi.changePassword(currentPassword, newPassword);
        if (data.success) {
          setSuccess(true);
          return { success: true };
        }
        const msg = data.errors?.[0]?.message ?? "Password change failed";
        setError(msg);
        return { success: false, error: msg };
      } catch (err: any) {
        const msg =
          err?.response?.data?.errors?.[0]?.message ??
          "Password change failed. Please try again.";
        setError(msg);
        return { success: false, error: msg };
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  const reset = useCallback(() => {
    setError(null);
    setSuccess(false);
  }, []);

  return { changePassword, isLoading, error, success, reset };
}
