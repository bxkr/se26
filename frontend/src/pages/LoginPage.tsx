import { useState, type FormEvent } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { strings } from "../lib/strings";
import { ApiError } from "../api/errors";
import { Button } from "../components/common/Button";
import { Input } from "../components/common/Input";

export function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const { login, isLoggingIn } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await login(username, password);
      navigate("/dashboard");
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setError(strings.login.invalid);
      } else {
        setError(strings.login.genericError);
      }
    }
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-6 bg-page px-4">
      <form
        onSubmit={handleSubmit}
        className="flex w-full max-w-sm flex-col gap-4 rounded-lg border border-border bg-surface p-6"
      >
        <h1 className="text-lg font-semibold text-ink">{strings.login.title}</h1>
        <Input
          label={strings.login.username}
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          autoComplete="username"
          required
        />
        <Input
          label={strings.login.password}
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete="current-password"
          required
        />
        {error && <p className="text-sm text-danger">{error}</p>}
        <Button type="submit" disabled={isLoggingIn}>
          {strings.login.submit}
        </Button>
        <Link to="/" className="text-center text-sm text-ink-secondary hover:text-ink">
          {strings.login.back}
        </Link>
      </form>
    </div>
  );
}
