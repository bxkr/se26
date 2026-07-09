interface StationTagProps {
  name?: string | null;
  wmoIndex: string;
  className?: string;
}

export function StationTag({ name, wmoIndex, className }: StationTagProps) {
  return (
    <span
      className={`inline-flex items-center border-l-2 border-accent bg-accent/5 py-0.5 pl-2 pr-2.5 font-mono text-xs text-ink ${className ?? ""}`}
    >
      {name ? (
        <>
          {name}
          <span className="ml-1.5 text-ink-muted">{wmoIndex}</span>
        </>
      ) : (
        wmoIndex
      )}
    </span>
  );
}
