import { DataTable, type DataTableColumn } from "../common/DataTable";
import { RoleBadge } from "../common/RoleBadge";
import { Button } from "../common/Button";
import { strings } from "../../lib/strings";
import type { AdminUser } from "../../types/admin";

interface UsersTableProps {
  users: AdminUser[];
  onToggleActive: (user: AdminUser) => void;
  onResetPassword: (user: AdminUser) => void;
  onChangeRole: (user: AdminUser) => void;
  onDelete: (user: AdminUser) => void;
}

export function UsersTable({ users, onToggleActive, onResetPassword, onChangeRole, onDelete }: UsersTableProps) {
  const columns: DataTableColumn<AdminUser>[] = [
    {
      key: "username",
      header: strings.admin.columns.username,
      render: (u) => <span className="font-mono">{u.username}</span>,
      sortValue: (u) => u.username,
    },
    {
      key: "role",
      header: strings.admin.columns.role,
      render: (u) => (
        <button onClick={() => onChangeRole(u)} title={strings.admin.columns.role}>
          <RoleBadge role={u.role} />
        </button>
      ),
      sortValue: (u) => u.role,
    },
    {
      key: "is_active",
      header: strings.admin.columns.active,
      render: (u) => (
        <button
          onClick={() => onToggleActive(u)}
          className={`h-5 w-9 rounded-full transition-colors ${u.is_active ? "bg-good" : "bg-border"}`}
          aria-label={strings.admin.columns.active}
        >
          <span
            className={`block h-4 w-4 translate-y-0.5 rounded-full bg-white transition-transform ${u.is_active ? "translate-x-[18px]" : "translate-x-0.5"}`}
          />
        </button>
      ),
      sortValue: (u) => (u.is_active ? 1 : 0),
    },
    {
      key: "created_at",
      header: strings.admin.columns.createdAt,
      render: (u) => <span className="font-mono text-xs">{u.created_at}</span>,
      sortValue: (u) => u.created_at,
    },
    {
      key: "actions",
      header: strings.admin.columns.actions,
      render: (u) => (
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => onResetPassword(u)}>
            {strings.admin.resetPassword}
          </Button>
          <Button variant="danger" onClick={() => onDelete(u)}>
            {strings.admin.deleteUser}
          </Button>
        </div>
      ),
    },
  ];

  return <DataTable columns={columns} rows={users} rowKey={(u) => u.id} />;
}
