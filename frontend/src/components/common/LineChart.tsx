import { ParentSize } from "@visx/responsive";
import { scaleLinear, scaleTime } from "@visx/scale";
import { LinePath } from "@visx/shape";
import { AxisBottom, AxisLeft } from "@visx/axis";
import { GridRows } from "@visx/grid";
import { curveMonotoneX } from "@visx/curve";
import { Group } from "@visx/group";
import { useTooltip, TooltipWithBounds, defaultStyles } from "@visx/tooltip";
import { useMemo, useCallback } from "react";

export interface LineSeries {
  key: string;
  label: string;
  color: string;
  points: { date: Date; value: number | null }[];
}

interface LineChartProps {
  series: LineSeries[];
  height?: number;
}

const margin = { top: 12, right: 16, bottom: 28, left: 48 };

function LineChartInner({ series, width, height }: LineChartProps & { width: number; height: number }) {
  const { tooltipData, tooltipLeft, tooltipTop, showTooltip, hideTooltip } = useTooltip<{
    date: Date;
    entries: { label: string; value: number | null; color: string }[];
  }>();

  const innerWidth = width - margin.left - margin.right;
  const innerHeight = height - margin.top - margin.bottom;

  const allPoints = useMemo(() => series.flatMap((s) => s.points), [series]);
  const allDates = allPoints.map((p) => p.date);
  const allValues = allPoints.map((p) => p.value).filter((v): v is number => v !== null);

  const xScale = useMemo(
    () =>
      scaleTime({
        domain: [
          Math.min(...allDates.map((d) => d.getTime())),
          Math.max(...allDates.map((d) => d.getTime())),
        ].map((t) => new Date(t)),
        range: [0, innerWidth],
      }),
    [allDates, innerWidth],
  );

  const yScale = useMemo(
    () =>
      scaleLinear({
        domain: [Math.min(0, ...allValues), Math.max(...allValues, 0)],
        range: [innerHeight, 0],
        nice: true,
      }),
    [allValues, innerHeight],
  );

  const handleMove = useCallback(
    (event: React.PointerEvent<SVGRectElement>) => {
      const rect = event.currentTarget.getBoundingClientRect();
      const x = event.clientX - rect.left;
      const targetTime = xScale.invert(x).getTime();

      const nearest = series.map((s) => {
        let closest = s.points[0];
        let minDiff = Infinity;
        for (const p of s.points) {
          const diff = Math.abs(p.date.getTime() - targetTime);
          if (diff < minDiff) {
            minDiff = diff;
            closest = p;
          }
        }
        return { label: s.label, value: closest?.value ?? null, color: s.color, date: closest?.date };
      });

      showTooltip({
        tooltipLeft: x,
        tooltipTop: innerHeight / 2,
        tooltipData: { date: nearest[0]?.date ?? new Date(targetTime), entries: nearest },
      });
    },
    [xScale, series, innerHeight, showTooltip],
  );

  if (width === 0 || allPoints.length === 0) return null;

  return (
    <div className="relative">
      <svg width={width} height={height}>
        <Group left={margin.left} top={margin.top}>
          <GridRows
            scale={yScale}
            width={innerWidth}
            stroke="rgb(var(--wp-border))"
            strokeDasharray="2,2"
          />
          {series.map((s) => (
            <LinePath
              key={s.key}
              data={s.points.filter((p) => p.value !== null)}
              x={(p) => xScale(p.date)}
              y={(p) => yScale(p.value as number)}
              stroke={s.color}
              strokeWidth={2}
              curve={curveMonotoneX}
            />
          ))}
          <AxisLeft
            scale={yScale}
            stroke="rgb(var(--wp-border))"
            tickStroke="rgb(var(--wp-border))"
            tickLabelProps={{ fill: "rgb(var(--wp-ink-muted))", fontSize: 10 }}
          />
          <AxisBottom
            top={innerHeight}
            scale={xScale}
            stroke="rgb(var(--wp-border))"
            tickStroke="rgb(var(--wp-border))"
            tickLabelProps={{ fill: "rgb(var(--wp-ink-muted))", fontSize: 10 }}
          />
          <rect
            width={innerWidth}
            height={innerHeight}
            fill="transparent"
            onPointerMove={handleMove}
            onPointerLeave={hideTooltip}
          />
        </Group>
      </svg>
      {series.length > 1 && (
        <div className="mt-2 flex flex-wrap gap-3 text-xs text-ink-secondary">
          {series.map((s) => (
            <span key={s.key} className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full" style={{ backgroundColor: s.color }} />
              {s.label}
            </span>
          ))}
        </div>
      )}
      {tooltipData && (
        <TooltipWithBounds
          left={tooltipLeft}
          top={tooltipTop}
          style={{
            ...defaultStyles,
            background: "rgb(var(--wp-surface))",
            color: "rgb(var(--wp-ink))",
            border: "1px solid rgb(var(--wp-border))",
          }}
        >
          <div className="font-mono text-xs">
            {tooltipData.date.toLocaleDateString("ru-RU")}
            {tooltipData.entries.map((e) => (
              <div key={e.label} style={{ color: e.color }}>
                {e.label}: {e.value ?? "—"}
              </div>
            ))}
          </div>
        </TooltipWithBounds>
      )}
    </div>
  );
}

export function LineChart({ series, height = 240 }: LineChartProps) {
  return (
    <div style={{ height }}>
      <ParentSize>
        {({ width }) => <LineChartInner series={series} width={width} height={height} />}
      </ParentSize>
    </div>
  );
}
