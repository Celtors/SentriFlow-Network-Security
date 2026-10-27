import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { bytes } from "../../lib/format";
import { useTrafficStore } from "../../store/trafficStore";

export default function SpeedChart() {
  const rates = useTrafficStore((state) => state.rates);
  return (
    <section className="panel">
      <div className="panel-heading">
        <h2>Traffic activity</h2>
        <div className="legend">
          <span className="accent">● Upload</span>
          <span className="muted">┄ Download</span>
        </div>
      </div>
      <p className="muted caption">
        Proxied payload bytes per second · live response chunks
      </p>
      <div className="chart">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={rates}>
            <defs>
              <linearGradient id="traffic-fill" x1="0" y1="0" x2="0" y2="1">
                <stop
                  offset="0%"
                  stopColor="var(--accent)"
                  stopOpacity={0.25}
                />
                <stop offset="100%" stopColor="var(--accent)" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="var(--border)" vertical={false} />
            <XAxis
              dataKey="time"
              minTickGap={55}
              tick={{ fill: "#a3a3a3", fontSize: 10 }}
            />
            <YAxis
              width={65}
              tickFormatter={bytes}
              tick={{ fill: "#a3a3a3", fontSize: 10 }}
            />
            <Tooltip
              contentStyle={{
                background: "#161616",
                border: "1px solid #303030",
              }}
              formatter={(value) => `${bytes(Number(value))}/s`}
            />
            <Area
              dataKey="upload"
              stroke="var(--accent)"
              fill="url(#traffic-fill)"
              isAnimationActive={false}
            />
            <Area
              dataKey="download"
              stroke="#b5b5b5"
              strokeDasharray="5 4"
              fill="transparent"
              isAnimationActive={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
      <small className="muted">
        Only requests routed through SentriFlow are counted. Approved request
        bodies and streamed response payloads; excludes protocol overhead.
      </small>
    </section>
  );
}
