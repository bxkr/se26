import { ParentSize } from "@visx/responsive";
import { scaleLinear } from "@visx/scale";
import { LinePath, AreaClosed } from "@visx/shape";
import { curveMonotoneX } from "@visx/curve";

interface SparklineProps {
  values: number[];
  color?: string;
}

function SparklineInner({ values, width, height, color }: SparklineProps & { width: number; height: number }) {
  if (values.length < 2 || width === 0) return null;

  const stroke = color ?? "rgb(var(--wp-gauge))";
  const xScale = scaleLinear({ domain: [0, values.length - 1], range: [2, width - 2] });
  const [min, max] = [Math.min(...values), Math.max(...values)];
  const yScale = scaleLinear({ domain: [min, max], range: [height - 3, 3] });

  return (
    <svg width={width} height={height}>
      <AreaClosed
        data={values}
        x={(_, i) => xScale(i)}
        y={(v) => yScale(v)}
        yScale={yScale}
        fill={stroke}
        fillOpacity={0.12}
        curve={curveMonotoneX}
      />
      <LinePath
        data={values}
        x={(_, i) => xScale(i)}
        y={(v) => yScale(v)}
        stroke={stroke}
        strokeWidth={1.5}
        curve={curveMonotoneX}
      />
    </svg>
  );
}

export function Sparkline({ values, color }: SparklineProps) {
  return (
    <div className="h-8 w-20 border-b border-border/70">
      <ParentSize>
        {({ width, height }) => (
          <SparklineInner values={values} width={width} height={height} color={color} />
        )}
      </ParentSize>
    </div>
  );
}
