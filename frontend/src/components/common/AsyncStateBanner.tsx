import { strings } from "../../lib/strings";
import { Button } from "./Button";

interface AsyncStateBannerProps {
  isFetching: boolean;
  error: Error | null;
  onRetry: () => void;
}

export function AsyncStateBanner({ isFetching, error, onRetry }: AsyncStateBannerProps) {
  if (error) {
    return (
      <div className="flex items-center justify-between gap-4 rounded-md border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-danger">
        <span>{error.message || strings.async.failed}</span>
        <Button variant="secondary" onClick={onRetry}>
          {strings.async.retry}
        </Button>
      </div>
    );
  }

  if (isFetching) {
    return (
      <div className="flex items-center gap-3 rounded-md border border-accent/30 bg-accent/10 px-4 py-3 text-sm text-accent">
        <span
          className="h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-accent border-t-transparent"
          aria-hidden
        />
        <span>{strings.async.pending}</span>
      </div>
    );
  }

  return null;
}
