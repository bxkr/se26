import { strings } from "../../lib/strings";
import { ApiError } from "../../api/errors";
import { Button } from "./Button";
import { BarographSpinner } from "./BarographSpinner";

interface AsyncStateBannerProps {
  isFetching: boolean;
  error: Error | null;
  onRetry: () => void;
}

function describeError(error: Error): string {
  if (error instanceof ApiError && error.code === "RATE_LIMITED") return strings.async.rateLimited;
  return error.message || strings.async.failed;
}

export function AsyncStateBanner({ isFetching, error, onRetry }: AsyncStateBannerProps) {
  if (error) {
    return (
      <div className="flex items-center justify-between gap-4 rounded-md border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-danger">
        <span>{describeError(error)}</span>
        <Button variant="secondary" onClick={onRetry}>
          {strings.async.retry}
        </Button>
      </div>
    );
  }

  if (isFetching) {
    return (
      <div className="flex items-center gap-3 rounded-md border border-accent/30 bg-accent/10 px-4 py-3 text-sm text-accent">
        <BarographSpinner />
        <span>{strings.async.pending}</span>
      </div>
    );
  }

  return null;
}
