import { useDeferredValue, useEffect, useRef, useState, type MouseEvent } from 'react'
import * as d3 from 'd3'
import { GitBranch, RotateCcw, Search, ZoomIn, ZoomOut } from 'lucide-react'

import { EmptyState } from '@/components/ui/EmptyState'
import { StatusBadge } from '@/components/ui/StatusBadge'
import type { OrgChartNode } from '@/lib/api/org-admin'
import { getEmployeeStatusTone } from '@/lib/status'

const VIEWPORT_WIDTH = 1400
const VIEWPORT_HEIGHT = 860
const INITIAL_TRANSFORM = d3.zoomIdentity.translate(520, 84).scale(0.7)

function cloneForCollapsedView(node: OrgChartNode, collapsedIds: Set<string>): OrgChartNode {
  return {
    ...node,
    direct_reports: collapsedIds.has(node.id)
      ? []
      : node.direct_reports.map((directReport) => cloneForCollapsedView(directReport, collapsedIds)),
  }
}

function collectDepartments(nodes: OrgChartNode[], bucket: string[] = []) {
  nodes.forEach((node) => {
    if (node.department && !bucket.includes(node.department)) {
      bucket.push(node.department)
    }
    collectDepartments(node.direct_reports, bucket)
  })
  return bucket
}

function countNodes(nodes: OrgChartNode[]): number {
  return nodes.reduce((total, node) => total + 1 + countNodes(node.direct_reports), 0)
}

function initialsFor(name: string) {
  return name
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? '')
    .join('')
}

function matchesSearch(node: OrgChartNode, searchValue: string) {
  if (!searchValue) return true
  const haystack = [node.name, node.employee_code, node.designation, node.department, node.email]
    .filter(Boolean)
    .join(' ')
    .toLowerCase()
  return haystack.includes(searchValue)
}

export function OrgChartD3({ data }: { data: OrgChartNode[] }) {
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedEmployeeId, setSelectedEmployeeId] = useState<string | null>(null)
  const [collapsedIds, setCollapsedIds] = useState<string[]>([])
  const deferredSearch = useDeferredValue(searchTerm.trim().toLowerCase())
  const svgRef = useRef<SVGSVGElement | null>(null)
  const viewportRef = useRef<SVGGElement | null>(null)
  const zoomBehaviorRef = useRef<d3.ZoomBehavior<SVGSVGElement, unknown> | null>(null)

  if (!data.length) {
    return (
      <EmptyState
        title="No reporting structure yet"
        description="Assign managers to employees and the interactive organisation chart will populate here."
        icon={GitBranch}
      />
    )
  }

  const collapsedTree = data.map((node) => cloneForCollapsedView(node, new Set(collapsedIds)))
  const syntheticRoot: OrgChartNode = {
    id: '__org_root__',
    name: 'Organisation root',
    email: '',
    employee_code: null,
    designation: null,
    department: null,
    status: 'ACTIVE',
    profile_picture: null,
    direct_reports: collapsedTree,
  }
  const hierarchy = d3.hierarchy(syntheticRoot, (node) => node.direct_reports)
  const chartHierarchy = d3.tree<OrgChartNode>().nodeSize([220, 132])(hierarchy)

  const nodes = chartHierarchy.descendants().filter((node) => node.data.id !== '__org_root__')
  const links = chartHierarchy.links().filter((link) => link.target.data.id !== '__org_root__')
  const departments = collectDepartments(data)
  const palette = [...d3.schemeTableau10, ...d3.schemeSet3]
  const colorScale = d3.scaleOrdinal<string, string>().domain(departments).range(palette)
  const matchingIds = new Set(nodes.filter((node) => matchesSearch(node.data, deferredSearch)).map((node) => node.data.id))
  const linkPath = d3
    .linkVertical<d3.HierarchyPointLink<OrgChartNode>, d3.HierarchyPointNode<OrgChartNode>>()
    .x((point) => point.x)
    .y((point) => point.y)
  const selectedNode = nodes.find((node) => node.data.id === selectedEmployeeId)?.data ?? null

  useEffect(() => {
    if (!svgRef.current || !viewportRef.current) {
      return
    }

    const svg = d3.select(svgRef.current)
    const viewport = d3.select(viewportRef.current)
    const zoomBehavior = d3
      .zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.45, 2])
      .on('zoom', (event) => {
        viewport.attr('transform', event.transform.toString())
      })
    zoomBehaviorRef.current = zoomBehavior
    svg.call(zoomBehavior)
    svg.call(zoomBehavior.transform, INITIAL_TRANSFORM)

    return () => {
      svg.on('.zoom', null)
    }
  }, [collapsedIds, data])

  const adjustZoom = (factor: number) => {
    if (!svgRef.current || !zoomBehaviorRef.current) return
    d3.select(svgRef.current).call(zoomBehaviorRef.current.scaleBy, factor)
  }

  const resetZoom = () => {
    if (!svgRef.current || !zoomBehaviorRef.current) return
    d3.select(svgRef.current).call(zoomBehaviorRef.current.transform, INITIAL_TRANSFORM)
  }

  const handleNodeClick = (
    event: MouseEvent<SVGGElement>,
    node: d3.HierarchyPointNode<OrgChartNode>,
  ) => {
    if ((event.metaKey || event.ctrlKey) && node.data.direct_reports.length > 0) {
      setCollapsedIds((current) =>
        current.includes(node.data.id)
          ? current.filter((item) => item !== node.data.id)
          : [...current, node.data.id],
      )
      return
    }
    setSelectedEmployeeId(node.data.id)
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
        <div className="flex flex-col gap-3 md:flex-row md:items-center">
          <label className="relative flex w-full max-w-md items-center">
            <Search className="pointer-events-none absolute left-4 h-4 w-4 text-[hsl(var(--muted-foreground))]" />
            <input
              className="field-input pl-11"
              placeholder="Search employees"
              value={searchTerm}
              onChange={(event) => setSearchTerm(event.target.value)}
            />
          </label>
          <div className="flex flex-wrap gap-2">
            <button type="button" className="btn-secondary px-3 py-2" onClick={() => adjustZoom(1.15)} aria-label="Zoom in">
              <ZoomIn className="h-4 w-4" />
            </button>
            <button type="button" className="btn-secondary px-3 py-2" onClick={() => adjustZoom(0.88)} aria-label="Zoom out">
              <ZoomOut className="h-4 w-4" />
            </button>
            <button type="button" className="btn-secondary px-3 py-2" onClick={resetZoom} aria-label="Reset view">
              <RotateCcw className="h-4 w-4" />
            </button>
          </div>
        </div>
        <div className="flex flex-wrap gap-2 text-sm text-[hsl(var(--muted-foreground))]">
          <StatusBadge tone="info">{countNodes(data)} people</StatusBadge>
          <StatusBadge tone="neutral">Ctrl/Cmd + click to collapse</StatusBadge>
        </div>
      </div>

      <div className="overflow-hidden rounded-[30px] border border-[hsl(var(--border))] bg-[radial-gradient(circle_at_top,_hsl(var(--brand)_/_0.08),_transparent_46%),linear-gradient(180deg,_hsl(var(--background)),_hsl(var(--background-subtle)))]">
        <svg
          ref={svgRef}
          viewBox={`0 0 ${VIEWPORT_WIDTH} ${VIEWPORT_HEIGHT}`}
          className="h-[42rem] w-full touch-none"
          role="img"
          aria-label="Interactive organisation chart"
        >
          <g ref={viewportRef}>
            <g>
              {links.map((link) => (
                <path
                  key={`${link.source.data.id}-${link.target.data.id}`}
                  d={linkPath(link) ?? ''}
                  fill="none"
                  stroke="hsl(var(--border))"
                  strokeWidth={2}
                  opacity={deferredSearch && !matchingIds.has(link.target.data.id) ? 0.18 : 0.7}
                />
              ))}
            </g>
            <g>
              {nodes.map((node) => {
                const isDimmed = Boolean(deferredSearch) && !matchingIds.has(node.data.id)
                const isSelected = selectedEmployeeId === node.data.id
                const departmentColor = colorScale(node.data.department || 'Unassigned')
                return (
                  <g
                    key={node.data.id}
                    data-testid={`org-chart-node-${node.data.id}`}
                    data-match-state={isDimmed ? 'dim' : 'match'}
                    transform={`translate(${node.x}, ${node.y})`}
                    style={{ opacity: isDimmed ? 0.18 : 1, cursor: 'pointer' }}
                    onClick={(event) => handleNodeClick(event, node)}
                  >
                    <rect
                      x={-92}
                      y={-30}
                      width={184}
                      height={68}
                      rx={22}
                      fill="hsl(var(--card))"
                      stroke={isSelected ? 'hsl(var(--brand))' : departmentColor}
                      strokeWidth={isSelected ? 3 : 2}
                    />
                    <circle cx={-60} cy={4} r={20} fill={departmentColor} opacity={0.9} />
                    <text x={-60} y={10} textAnchor="middle" fontSize="13" fontWeight="700" fill="white">
                      {initialsFor(node.data.name)}
                    </text>
                    <text x={-28} y={-6} fontSize="15" fontWeight="700" fill="hsl(var(--foreground-strong))">
                      {node.data.name}
                    </text>
                    <text x={-28} y={15} fontSize="12" fill="hsl(var(--muted-foreground))">
                      {[node.data.designation, node.data.department].filter(Boolean).join(' • ') || 'Role details pending'}
                    </text>
                    {node.data.direct_reports.length > 0 ? (
                      <text x={68} y={18} fontSize="16" fontWeight="700" fill="hsl(var(--muted-foreground))">
                        {collapsedIds.includes(node.data.id) ? '+' : '−'}
                      </text>
                    ) : null}
                  </g>
                )
              })}
            </g>
          </g>
        </svg>
      </div>

      <div className="grid gap-4 xl:grid-cols-[0.8fr_1.2fr]">
        <div className="surface-muted rounded-[24px] p-5">
          <p className="text-sm font-medium text-[hsl(var(--foreground-strong))]">Node details</p>
          {selectedNode ? (
            <div className="mt-4 space-y-3 text-sm text-[hsl(var(--muted-foreground))]">
              <div>
                <p className="font-semibold text-[hsl(var(--foreground-strong))]">{selectedNode.name}</p>
                <p>{selectedNode.email}</p>
              </div>
              <div className="flex flex-wrap gap-2">
                <StatusBadge tone={getEmployeeStatusTone(selectedNode.status)}>{selectedNode.status}</StatusBadge>
                {selectedNode.employee_code ? <StatusBadge tone="neutral">{selectedNode.employee_code}</StatusBadge> : null}
              </div>
              <p>{[selectedNode.designation, selectedNode.department].filter(Boolean).join(' • ') || 'Role details not assigned'}</p>
            </div>
          ) : (
            <p className="mt-4 text-sm text-[hsl(var(--muted-foreground))]">
              Click a node to inspect the employee summary. Use Ctrl/Cmd + click to collapse or expand a reporting branch.
            </p>
          )}
        </div>

        <div className="surface-muted rounded-[24px] p-5">
          <p className="text-sm font-medium text-[hsl(var(--foreground-strong))]">Department legend</p>
          <div className="mt-4 flex flex-wrap gap-2">
            {departments.map((department) => (
              <span
                key={department}
                className="inline-flex items-center gap-2 rounded-full border border-[hsl(var(--border))] px-3 py-1.5 text-sm text-[hsl(var(--foreground-strong))]"
              >
                <span
                  className="h-2.5 w-2.5 rounded-full"
                  style={{ backgroundColor: colorScale(department) }}
                  aria-hidden="true"
                />
                {department}
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
