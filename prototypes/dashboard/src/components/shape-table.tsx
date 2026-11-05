import * as React from "react"

import { Badge } from "@/components/ui/badge"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import shapes from "@/data/shapes.json"

type Shape = {
  name: string
  kind: string
  cells: number
  schlafli: string
  family: string
  dims: number
}

// Exported straight from hyperspace.geometry.SHAPES, already ordered
// 4D first, then by cell count.
const ALL = shapes as Shape[]

const GROUPS = [
  { key: "all", label: "All", match: () => true },
  { key: "4d", label: "4-polytopes", match: (s: Shape) => s.dims === 4 },
  {
    key: "regular",
    label: "Regular",
    match: (s: Shape) => s.family === "Regular polytopes",
  },
  {
    key: "stars",
    label: "Stars",
    match: (s: Shape) => s.family.startsWith("Star"),
  },
  {
    key: "solids",
    label: "Solids",
    match: (s: Shape) => s.family.endsWith("solids"),
  },
  {
    key: "surfaces",
    label: "Surfaces",
    match: (s: Shape) => s.family.startsWith("Surfaces"),
  },
] as const

export function ShapeTable() {
  const [tab, setTab] = React.useState<string>("all")

  const rows = React.useMemo(() => {
    const g = GROUPS.find((g) => g.key === tab) ?? GROUPS[0]
    return ALL.filter(g.match).slice(0, 12)
  }, [tab])

  const count = React.useMemo(() => {
    const g = GROUPS.find((g) => g.key === tab) ?? GROUPS[0]
    return ALL.filter(g.match).length
  }, [tab])

  return (
    <div className="flex w-full flex-col gap-4 px-4 lg:px-6">
      <Tabs value={tab} onValueChange={setTab}>
        <div className="flex items-center justify-between">
          <TabsList>
            {GROUPS.map((g) => (
              <TabsTrigger key={g.key} value={g.key}>
                {g.label}
              </TabsTrigger>
            ))}
          </TabsList>
          <span className="text-muted-foreground hidden text-sm sm:block">
            Showing {rows.length} of {count}
          </span>
        </div>
      </Tabs>

      <div className="overflow-hidden rounded-lg border">
        <Table>
          <TableHeader className="bg-muted sticky top-0 z-10">
            <TableRow>
              <TableHead>Shape</TableHead>
              <TableHead className="hidden md:table-cell">Kind</TableHead>
              <TableHead>Schläfli</TableHead>
              <TableHead className="text-center">Dim</TableHead>
              <TableHead className="text-right">Cells</TableHead>
              <TableHead className="hidden lg:table-cell">Family</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((s) => (
              <TableRow key={s.name}>
                <TableCell className="font-medium">{s.name}</TableCell>
                <TableCell className="text-muted-foreground hidden md:table-cell">
                  {s.kind}
                </TableCell>
                <TableCell className="font-mono text-xs">
                  {s.schlafli || "—"}
                </TableCell>
                <TableCell className="text-muted-foreground text-center font-mono text-xs">
                  {s.dims}D
                </TableCell>
                <TableCell className="text-right tabular-nums">
                  {s.cells > 0 ? s.cells : "—"}
                </TableCell>
                <TableCell className="hidden lg:table-cell">
                  <Badge variant="outline">{s.family}</Badge>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}
