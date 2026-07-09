import { Link } from "react-router-dom";
import { strings } from "../lib/strings";

export function NotFoundPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-page">
      <p className="text-lg text-ink">{strings.common.notFound}</p>
      <Link to="/" className="text-accent hover:underline">
        {strings.login.back}
      </Link>
    </div>
  );
}
