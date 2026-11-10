import * as React from "react"
import { Area, AreaChart, CartesianGrid, XAxis, YAxis } from "recharts"

import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { BANDS, makeTicks } from "@/data/bands"

// CEIL in bands.py — the asymptotic ceiling of the fader output.
const CEIL = 2.6

const ALL = makeTicks(180)

// Six independent series of the same unit, so: small multiples on a shared
// scale, one facet per band. Identity comes from the facet label, not from
// colour — the preset's chart ramp is a 5-step greyscale (a sequential ramp),
// which cannot carry six categories.
const CHART_CONFIG = {
  level: { label: "Level", color: "var(--chart-3)" },
} satisfies ChartConfig

export function BandChart() {
  const [range, setRange] = React.useState("180")

  const data = React.useMemo(
    () => ALL.slice(ALL.length - Number(range)),
    [range]
  )

  return (
    <Card className="@container/card">
      <CardHeader>
        <CardTitle>Band levels</CardTitle>
        <CardDescription>
          Each frequency band drives one rotation plane. Shared scale, 0–
          {CEIL}.
        </CardDescription>
        <CardAction>
          <ToggleGroup
            type="single"
            value={range}
            onValueChange={(v) => v && setRange(v)}
            variant="outline"
            className="hidden @[767px]/card:flex"
          >
            <ToggleGroupItem value="180">3 s</ToggleGroupItem>
            <ToggleGroupItem value="90">1.5 s</ToggleGroupItem>
            <ToggleGroupItem value="30">0.5 s</ToggleGroupItem>
          </ToggleGroup>
        </CardAction>
      </CardHeader>

      <CardContent className="grid grid-cols-1 gap-x-6 gap-y-5 @2xl/card:grid-cols-2 @5xl/card:grid-cols-3">
        {BANDS.map((b) => {
          const series = data.map((row) => ({ t: row.t, level: row[b.name] }))
          const latest = series.at(-1)?.level ?? 0
          return (
            <div key={b.name} className="flex flex-col gap-1">
              <div className="flex items-baseline justify-between">
                <div className="flex items-baseline gap-2">
                  <span className="font-mono text-xs font-medium">
                    {b.name}
                  </span>
                  <span className="text-muted-foreground font-mono text-xs">
                    {b.plane}
                  </span>
                </div>
                <span className="text-muted-foreground font-mono text-xs tabular-nums">
                  {latest.toFixed(2)}
                </span>
              </div>

              <ChartContainer
                config={CHART_CONFIG}
                className="aspect-auto h-[96px] w-full"
              >
                <AreaChart
                  data={series}
                  margin={{ top: 4, right: 4, left: 0, bottom: 0 }}
                >
                  <defs>
                    <linearGradient
                      id={`fill-${b.name}`}
                      x1="0"
                      y1="0"
                      x2="0"
                      y2="1"
                    >
                      <stop
                        offset="5%"
                        stopColor="var(--color-level)"
                        stopOpacity={0.5}
                      />
                      <stop
                        offset="95%"
                        stopColor="var(--color-level)"
                        stopOpacity={0.05}
                      />
                    </linearGradient>
                  </defs>
                  <CartesianGrid vertical={false} />
                  <XAxis dataKey="t" hide />
                  <YAxis
                    domain={[0, CEIL]}
                    ticks={[0, 1.3, CEIL]}
                    tickLine={false}
                    axisLine={false}
                    tickMargin={4}
                    width={26}
                    tick={{ fontSize: 10 }}
                  />
                  <ChartTooltip
                    cursor={{ strokeDasharray: "3 3" }}
                    content={
                      <ChartTooltipContent
                        indicator="dot"
                        labelFormatter={(_, p) =>
                          `${b.name} · ${b.plane} · ${(
                            Number(p?.[0]?.payload?.t ?? 0) / 60
                          ).toFixed(2)}s`
                        }
                      />
                    }
                  />
                  <Area
                    dataKey="level"
                    type="natural"
                    fill={`url(#fill-${b.name})`}
                    stroke="var(--color-level)"
                    strokeWidth={2}
                  />
                </AreaChart>
              </ChartContainer>
            </div>
          )
        })}
      </CardContent>
    </Card>
  )
}
