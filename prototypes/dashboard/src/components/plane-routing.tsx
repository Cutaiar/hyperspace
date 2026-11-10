import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { BANDS, makeTicks } from "@/data/bands"

const LAST = makeTicks(180).at(-1)!

export function PlaneRouting() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Plane routing</CardTitle>
        <CardDescription>
          Band to rotation plane, with the latest level
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {BANDS.map((b) => {
          const level = LAST[b.name] ?? 0
          const pct = Math.min(100, (level / 2.6) * 100)
          return (
            <div key={b.name} className="flex items-center gap-3">
              <span className="w-12 font-mono text-xs font-medium">
                {b.name}
              </span>
              <Badge variant="secondary" className="w-10 justify-center">
                {b.plane}
              </Badge>
              <div className="bg-muted relative h-2 flex-1 overflow-hidden rounded-full">
                <div
                  className="bg-primary absolute inset-y-0 left-0 rounded-full"
                  style={{ width: `${pct}%` }}
                />
              </div>
              <span className="text-muted-foreground w-28 text-right font-mono text-xs tabular-nums">
                {b.lo}–{b.hi} Hz
              </span>
              <span className="w-10 text-right font-mono text-xs tabular-nums">
                {b.dir > 0 ? "+" : "−"}
                {level.toFixed(2)}
              </span>
            </div>
          )
        })}
      </CardContent>
    </Card>
  )
}
