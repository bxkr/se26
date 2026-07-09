import { useState, type FormEvent } from "react";
import { Modal } from "../common/Modal";
import { Input } from "../common/Input";
import { Button } from "../common/Button";
import { strings } from "../../lib/strings";

interface ResetPasswordModalProps {
  username: string;
  onClose: () => void;
  onSubmit: (newPassword: string) => Promise<void>;
  isSubmitting: boolean;
  error: string | null;
}

export function ResetPasswordModal({ username, onClose, onSubmit, isSubmitting, error }: ResetPasswordModalProps) {
  const [password, setPassword] = useState("");

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    await onSubmit(password);
  }

  return (
    <Modal title={`${strings.admin.modalResetTitle}: ${username}`} onClose={onClose}>
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <Input
          label={strings.admin.newPassword}
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
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
