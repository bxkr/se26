import { useState } from "react";
import clsx from "clsx";
import { ChevronUpIcon, ChevronDownIcon } from "./Icons";

export interface DataTableColumn<T> {
  key: string;
  header: string;
  render: (row: T) => React.ReactNode;
  sortValue?: (row: T) => number | string | null;
  align?: "left" | "right";
}

interface DataTableProps<T> {
  columns: DataTableColumn<T>[];
  rows: T[];
  rowKey: (row: T) => string;
  onRowClick?: (row: T) => void;
  emptyMessage?: string;
}

export function DataTable<T>({ columns, rows, rowKey, onRowClick, emptyMessage }: DataTableProps<T>) {
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

  function handleSort(col: DataTableColumn<T>) {
    if (!col.sortValue) return;
    if (sortKey === col.key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(col.key);
      setSortDir("desc");
    }
  }

  const sortedRows = (() => {
    const col = columns.find((c) => c.key === sortKey);
    if (!col?.sortValue) return rows;
    const withValues = rows.map((r) => ({ r, v: col.sortValue!(r) }));
    withValues.sort((a, b) => {
      if (a.v === null) return 1;
      if (b.v === null) return -1;
      const diff = a.v < b.v ? -1 : a.v > b.v ? 1 : 0;
      return sortDir === "asc" ? diff : -diff;
    });
    return withValues.map((x) => x.r);
  })();

  if (rows.length === 0) {
    return <p className="py-8 text-center text-sm text-ink-muted">{emptyMessage}</p>;
  }

  return (
    <div className="overflow-x-auto rounded-md border border-border">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="border-b border-border bg-page">
            {columns.map((col) => (
              <th
                key={col.key}
                onClick={() => handleSort(col)}
                className={clsx(
                  "px-3 py-2 text-xs font-medium uppercase tracking-wide text-ink-muted",
                  col.align === "right" ? "text-right" : "text-left",
                  col.sortValue && "cursor-pointer select-none hover:text-ink",
                )}
              >
                <span className="inline-flex items-center gap-1">
                  {col.header}
                  {sortKey === col.key &&
                    (sortDir === "asc" ? (
                      <ChevronUpIcon width={12} height={12} />
                    ) : (
                      <ChevronDownIcon width={12} height={12} />
                    ))}
                </span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sortedRows.map((row) => (
            <tr
              key={rowKey(row)}
              onClick={() => onRowClick?.(row)}
              className={clsx(
                "border-b border-border last:border-0",
                onRowClick && "cursor-pointer hover:bg-page",
              )}
            >
              {columns.map((col) => (
                <td
                  key={col.key}
                  className={clsx("px-3 py-2", col.align === "right" ? "text-right" : "text-left")}
                >
                  {col.render(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
