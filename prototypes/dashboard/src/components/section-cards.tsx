import { TrendingDown, TrendingUp } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import {
  Card,
  CardAction,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"

type Stat = {
  label: string
  value: string
  delta: string
  up: boolean
  headline: string
  detail: string
}

const STATS: Stat[] = [
  {
    label: "Shapes in catalog",
    value: "101",
    delta: "+43",
    up: true,
    headline: "Catalog complete",
    detail: "61 four-dimensional, 40 three-dimensional",
  },
  {
    label: "Frame rate",
    value: "59.6 fps",
    delta: "-0.4",
    up: false,
    headline: "Holding the vsync budget",
    detail: "16.8 ms mean frame, 2.1 ms headroom",
  },
  {
    label: "Rotation planes",
    value: "6 / 6",
    delta: "all live",
    up: true,
    headline: "Every plane driven",
    detail: "XY · XZ · YZ · XW · YW · ZW",
  },
  {
    label: "Analyzer load",
    value: "4.5%",
    delta: "+0.3%",
    up: true,
    headline: "FFT comfortably under budget",
    detail: "2048-point window at 60 Hz",
  },
]

export function SectionCards() {
  return (
    <div className="grid grid-cols-1 gap-4 px-4 *:data-[slot=card]:bg-gradient-to-t *:data-[slot=card]:from-primary/5 *:data-[slot=card]:to-card *:data-[slot=card]:shadow-xs lg:px-6 @xl/main:grid-cols-2 @5xl/main:grid-cols-4 dark:*:data-[slot=card]:bg-card">
      {STATS.map((s) => {
        const Arrow = s.up ? TrendingUp : TrendingDown
        return (
          <Card key={s.label} className="@container/card">
            <CardHeader>
              <CardDescription>{s.label}</CardDescription>
              <CardTitle className="text-2xl font-semibold tabular-nums @[250px]/card:text-3xl">
                {s.value}
              </CardTitle>
              <CardAction>
                <Badge variant="outline">
                  <Arrow />
                  {s.delta}
                </Badge>
              </CardAction>
            </CardHeader>
            <CardFooter className="flex-col items-start gap-1.5 text-sm">
              <div className="line-clamp-1 flex gap-2 font-medium">
                {s.headline} <Arrow className="size-4" />
              </div>
              <div className="text-muted-foreground">{s.detail}</div>
            </CardFooter>
          </Card>
        )
      })}
    </div>
  )
}
