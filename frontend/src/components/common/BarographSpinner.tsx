export function BarographSpinner() {
  return (
    <svg viewBox="0 0 64 16" className="h-4 w-10 shrink-0" aria-hidden>
      <path
        d="M0,10 L7,10 L11,3 L15,14 L19,5 L23,12 L27,8 L31,10 L64,10"
        fill="none"
        stroke="rgb(var(--wp-border))"
        strokeWidth={2}
      />
      <path
        d="M0,10 L7,10 L11,3 L15,14 L19,5 L23,12 L27,8 L31,10 L64,10"
        pathLength={2}
        fill="none"
        stroke="rgb(var(--wp-gauge))"
        strokeWidth={2}
        strokeLinecap="round"
        strokeDasharray="0.5 1.5"
        className="animate-barograph"
      />
    </svg>
  );
}
