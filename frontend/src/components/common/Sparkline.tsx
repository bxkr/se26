import { ParentSize } from "@visx/responsive";
import { scaleLinear } from "@visx/scale";
import { LinePath } from "@visx/shape";
import { curveMonotoneX } from "@visx/curve";

interface SparklineProps {
  values: number[];
  color?: string;
}

function SparklineInner({ values, width, height, color }: SparklineProps & { width: number; height: number }) {
  if (values.length < 2 || width === 0) return null;

  const xScale = scaleLinear({ domain: [0, values.length - 1], range: [2, width - 2] });
  const [min, max] = [Math.min(...values), Math.max(...values)];
  const yScale = scaleLinear({ domain: [min, max], range: [height - 2, 2] });

  return (
    <svg width={width} height={height}>
      <LinePath
        data={values}
        x={(_, i) => xScale(i)}
        y={(v) => yScale(v)}
        stroke={color ?? "rgb(var(--wp-accent))"}
        strokeWidth={2}
        curve={curveMonotoneX}
      />
    </svg>
  );
}

export function Sparkline({ values, color }: SparklineProps) {
  return (
    <div className="h-8 w-20">
      <ParentSize>
        {({ width, height }) => (
          <SparklineInner values={values} width={width} height={height} color={color} />
        )}
      </ParentSize>
    </div>
  );
}
