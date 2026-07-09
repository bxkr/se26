import { useState, type FormEvent } from "react";
import { Modal } from "../common/Modal";
import { Input } from "../common/Input";
import { Select } from "../common/Select";
import { Button } from "../common/Button";
import { strings } from "../../lib/strings";
import type { CreateUserRequest } from "../../types/admin";

interface CreateUserModalProps {
  onClose: () => void;
  onSubmit: (body: CreateUserRequest) => Promise<void>;
  isSubmitting: boolean;
  error: string | null;
}

export function CreateUserModal({ onClose, onSubmit, isSubmitting, error }: CreateUserModalProps) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<"user" | "admin">("user");

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    await onSubmit({ username, password, role });
  }

  return (
    <Modal title={strings.admin.modalCreateTitle} onClose={onClose}>
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <Input label={strings.admin.columns.username} value={username} onChange={(e) => setUsername(e.target.value)} required />
        <Input
          label={strings.login.password}
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        <Select label={strings.admin.columns.role} value={role} onChange={(e) => setRole(e.target.value as "user" | "admin")}>
          <option value="user">{strings.roles.user}</option>
          <option value="admin">{strings.roles.admin}</option>
        </Select>
        {error && <p className="text-sm text-danger">{error}</p>}
        <div className="flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            {strings.admin.cancel}
          </Button>
          <Button type="submit" disabled={isSubmitting}>
            {strings.admin.save}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
