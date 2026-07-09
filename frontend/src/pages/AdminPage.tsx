import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { PageContainer } from "../components/layout/PageContainer";
import { Button } from "../components/common/Button";
import { UsersTable } from "../components/admin/UsersTable";
import { CreateUserModal } from "../components/admin/CreateUserModal";
import { ResetPasswordModal } from "../components/admin/ResetPasswordModal";
import * as adminApi from "../api/endpoints/admin";
import { ApiError } from "../api/errors";
import { queryKeys } from "../lib/queryKeys";
import { strings } from "../lib/strings";
import type { AdminUser } from "../types/admin";

export function AdminPage() {
  const queryClient = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [resetTarget, setResetTarget] = useState<AdminUser | null>(null);

  const usersQuery = useQuery({ queryKey: queryKeys.adminUsers, queryFn: adminApi.listUsers });

  function invalidate() {
    queryClient.invalidateQueries({ queryKey: queryKeys.adminUsers });
  }

  const createMutation = useMutation({
    mutationFn: adminApi.createUser,
    onSuccess: () => {
      invalidate();
      setShowCreate(false);
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, body }: { id: string; body: Parameters<typeof adminApi.updateUser>[1] }) =>
      adminApi.updateUser(id, body),
    onSuccess: invalidate,
  });

  const deleteMutation = useMutation({
    mutationFn: adminApi.deleteUser,
    onSuccess: invalidate,
  });

  const resetMutation = useMutation({
    mutationFn: ({ id, newPassword }: { id: string; newPassword: string }) =>
      adminApi.resetPassword(id, { new_password: newPassword }),
    onSuccess: () => setResetTarget(null),
  });

  if (usersQuery.error instanceof ApiError && usersQuery.error.status === 403) {
    return (
      <PageContainer>
        <p className="text-center text-sm text-ink-muted">{strings.admin.forbidden}</p>
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="font-display text-xl font-semibold text-ink">{strings.admin.title}</h1>
        <Button onClick={() => setShowCreate(true)}>{strings.admin.createUser}</Button>
      </div>

      <UsersTable
        users={usersQuery.data ?? []}
        onToggleActive={(u) => updateMutation.mutate({ id: u.id, body: { is_active: !u.is_active } })}
        onChangeRole={(u) =>
          updateMutation.mutate({ id: u.id, body: { role: u.role === "admin" ? "user" : "admin" } })
        }
        onResetPassword={setResetTarget}
        onDelete={(u) => {
          if (confirm(strings.admin.confirmDelete)) deleteMutation.mutate(u.id);
        }}
      />

      {showCreate && (
        <CreateUserModal
          onClose={() => setShowCreate(false)}
          onSubmit={async (body) => {
            await createMutation.mutateAsync(body);
          }}
          isSubmitting={createMutation.isPending}
          error={createMutation.error?.message ?? null}
        />
      )}

      {resetTarget && (
        <ResetPasswordModal
          username={resetTarget.username}
          onClose={() => setResetTarget(null)}
          onSubmit={async (newPassword) => {
            await resetMutation.mutateAsync({ id: resetTarget.id, newPassword });
          }}
          isSubmitting={resetMutation.isPending}
          error={resetMutation.error?.message ?? null}
        />
      )}
    </PageContainer>
  );
}
