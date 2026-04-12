import { useMemo, useState } from 'react'
import { BriefcaseBusiness, Wrench } from 'lucide-react'
import { toast } from 'sonner'

import { EmptyState } from '@/components/ui/EmptyState'
import { PageHeader } from '@/components/ui/PageHeader'
import { SectionCard } from '@/components/ui/SectionCard'
import { SkeletonPageHeader, SkeletonTable } from '@/components/ui/Skeleton'
import { StatusBadge } from '@/components/ui/StatusBadge'
import {
  useAssetCategories,
  useAssetItems,
  useAssetMaintenance,
  useCreateAssetCategory,
  useCreateAssetItem,
  useCreateAssetMaintenance,
} from '@/hooks/useOrgAdmin'
import { getErrorMessage } from '@/lib/errors'
import { formatDate, formatINR, startCase } from '@/lib/format'
import { getAssetLifecycleTone } from '@/lib/status'

const CONDITION_OPTIONS = ['NEW', 'GOOD', 'FAIR', 'POOR', 'DAMAGED'] as const
const STATUS_FILTER_OPTIONS = ['AVAILABLE', 'ASSIGNED', 'IN_MAINTENANCE', 'LOST', 'RETIRED'] as const

export function AssetsInventoryPage() {
  const [statusFilter, setStatusFilter] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('')
  const [categoryForm, setCategoryForm] = useState({ name: '', description: '' })
  const [assetForm, setAssetForm] = useState({
    name: '',
    asset_tag: '',
    serial_number: '',
    vendor: '',
    category: '',
    condition: 'GOOD',
  })
  const [maintenanceForm, setMaintenanceForm] = useState({
    asset: '',
    maintenance_type: '',
    scheduled_date: '',
    vendor: '',
  })

  const { data: categories = [], isLoading: areCategoriesLoading } = useAssetCategories()
  const { data: items = [], isLoading: areItemsLoading } = useAssetItems({
    status: statusFilter || undefined,
    category: categoryFilter || undefined,
  })
  const { data: maintenanceRecords = [], isLoading: isMaintenanceLoading } = useAssetMaintenance()
  const createCategoryMutation = useCreateAssetCategory()
  const createAssetMutation = useCreateAssetItem()
  const createMaintenanceMutation = useCreateAssetMaintenance()

  const categoryOptions = useMemo(() => categories.map((category) => ({ value: category.id, label: category.name })), [categories])

  const handleCreateCategory = async (event: React.FormEvent) => {
    event.preventDefault()
    try {
      await createCategoryMutation.mutateAsync({
        name: categoryForm.name,
        description: categoryForm.description,
      })
      toast.success('Asset category created.')
      setCategoryForm({ name: '', description: '' })
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to create the asset category.'))
    }
  }

  const handleCreateAsset = async (event: React.FormEvent) => {
    event.preventDefault()
    try {
      await createAssetMutation.mutateAsync({
        name: assetForm.name,
        asset_tag: assetForm.asset_tag,
        serial_number: assetForm.serial_number,
        vendor: assetForm.vendor,
        category: assetForm.category || null,
        condition: assetForm.condition,
      })
      toast.success('Asset added to inventory.')
      setAssetForm({
        name: '',
        asset_tag: '',
        serial_number: '',
        vendor: '',
        category: '',
        condition: 'GOOD',
      })
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to add this asset to inventory.'))
    }
  }

  const handleScheduleMaintenance = async (event: React.FormEvent) => {
    event.preventDefault()
    try {
      await createMaintenanceMutation.mutateAsync({
        asset: maintenanceForm.asset,
        maintenance_type: maintenanceForm.maintenance_type,
        scheduled_date: maintenanceForm.scheduled_date,
        vendor: maintenanceForm.vendor,
      })
      toast.success('Maintenance scheduled.')
      setMaintenanceForm({ asset: '', maintenance_type: '', scheduled_date: '', vendor: '' })
    } catch (error) {
      toast.error(getErrorMessage(error, 'Unable to schedule maintenance for this asset.'))
    }
  }

  if (areCategoriesLoading || areItemsLoading || isMaintenanceLoading) {
    return (
      <div className="space-y-5">
        <SkeletonPageHeader />
        <SkeletonTable rows={6} />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Operations"
        title="Asset inventory"
        description="Manage the catalogue of issued equipment, track who currently holds each item, and schedule maintenance without leaving the admin workspace."
      />

      <div className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        <SectionCard title="Add category" description="Keep asset taxonomy clean so issue and recovery flows stay searchable.">
          <form className="grid gap-4" onSubmit={handleCreateCategory}>
            <div>
              <label className="field-label" htmlFor="asset-category-name">
                Category name
              </label>
              <input
                id="asset-category-name"
                className="field-input"
                value={categoryForm.name}
                onChange={(event) => setCategoryForm((current) => ({ ...current, name: event.target.value }))}
                placeholder="Laptops"
              />
            </div>
            <div>
              <label className="field-label" htmlFor="asset-category-description">
                Description
              </label>
              <textarea
                id="asset-category-description"
                className="field-input min-h-[104px]"
                value={categoryForm.description}
                onChange={(event) => setCategoryForm((current) => ({ ...current, description: event.target.value }))}
                placeholder="Portable devices issued to engineers and managers."
              />
            </div>
            <button type="submit" className="btn-secondary" disabled={createCategoryMutation.isPending}>
              Add category
            </button>
          </form>
        </SectionCard>

        <SectionCard title="Add asset" description="Capture the operational identifiers needed before the item is issued.">
          <form className="grid gap-4 md:grid-cols-2" onSubmit={handleCreateAsset}>
            <div className="md:col-span-2">
              <label className="field-label" htmlFor="asset-name">
                Asset name
              </label>
              <input
                id="asset-name"
                className="field-input"
                value={assetForm.name}
                onChange={(event) => setAssetForm((current) => ({ ...current, name: event.target.value }))}
                placeholder="MacBook Pro"
              />
            </div>
            <div>
              <label className="field-label" htmlFor="asset-tag">
                Asset tag
              </label>
              <input
                id="asset-tag"
                className="field-input"
                value={assetForm.asset_tag}
                onChange={(event) => setAssetForm((current) => ({ ...current, asset_tag: event.target.value }))}
                placeholder="LAP-300"
              />
            </div>
            <div>
              <label className="field-label" htmlFor="asset-serial-number">
                Serial number
              </label>
              <input
                id="asset-serial-number"
                className="field-input"
                value={assetForm.serial_number}
                onChange={(event) => setAssetForm((current) => ({ ...current, serial_number: event.target.value }))}
                placeholder="SN-123"
              />
            </div>
            <div>
              <label className="field-label" htmlFor="asset-vendor">
                Vendor
              </label>
              <input
                id="asset-vendor"
                className="field-input"
                value={assetForm.vendor}
                onChange={(event) => setAssetForm((current) => ({ ...current, vendor: event.target.value }))}
                placeholder="Apple"
              />
            </div>
            <div>
              <label className="field-label" htmlFor="asset-category">
                Category
              </label>
              <select
                id="asset-category"
                className="field-input"
                value={assetForm.category}
                onChange={(event) => setAssetForm((current) => ({ ...current, category: event.target.value }))}
              >
                <option value="">Uncategorized</option>
                {categoryOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="field-label" htmlFor="asset-condition">
                Condition
              </label>
              <select
                id="asset-condition"
                className="field-input"
                value={assetForm.condition}
                onChange={(event) => setAssetForm((current) => ({ ...current, condition: event.target.value }))}
              >
                {CONDITION_OPTIONS.map((option) => (
                  <option key={option} value={option}>
                    {startCase(option)}
                  </option>
                ))}
              </select>
            </div>
            <div className="md:col-span-2">
              <button type="submit" className="btn-primary" disabled={createAssetMutation.isPending}>
                Add asset
              </button>
            </div>
          </form>
        </SectionCard>
      </div>

      <SectionCard title="Inventory ledger" description="Filter by lifecycle status or category to focus on available stock, assigned items, or recovery work.">
        <div className="mb-5 grid gap-4 md:grid-cols-2">
          <div>
            <label className="field-label" htmlFor="asset-status-filter">
              Status filter
            </label>
            <select id="asset-status-filter" className="field-input" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
              <option value="">All statuses</option>
              {STATUS_FILTER_OPTIONS.map((status) => (
                <option key={status} value={status}>
                  {startCase(status)}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="field-label" htmlFor="asset-category-filter">
              Category filter
            </label>
            <select id="asset-category-filter" className="field-input" value={categoryFilter} onChange={(event) => setCategoryFilter(event.target.value)}>
              <option value="">All categories</option>
              {categoryOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {items.length ? (
          <div className="grid gap-4 lg:grid-cols-2">
            {items.map((item) => (
              <div key={item.id} className="rounded-[24px] border border-[hsl(var(--border))] bg-white/70 p-5">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="font-semibold text-[hsl(var(--foreground-strong))]">{item.name}</p>
                    <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">
                      {item.asset_tag || 'No asset tag'} • {item.category_name || 'Uncategorized'}
                    </p>
                    <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">Category: {item.category_name || 'Uncategorized'}</p>
                  </div>
                  <StatusBadge tone={getAssetLifecycleTone(item.lifecycle_status)}>{item.lifecycle_status}</StatusBadge>
                </div>
                <dl className="mt-4 grid gap-3 sm:grid-cols-2">
                  <div>
                    <dt className="text-xs uppercase tracking-[0.12em] text-[hsl(var(--muted-foreground))]">Vendor</dt>
                    <dd className="mt-1 text-sm text-[hsl(var(--foreground-strong))]">{item.vendor || 'Not recorded'}</dd>
                  </div>
                  <div>
                    <dt className="text-xs uppercase tracking-[0.12em] text-[hsl(var(--muted-foreground))]">Cost</dt>
                    <dd className="mt-1 text-sm text-[hsl(var(--foreground-strong))]">{formatINR(item.purchase_cost)}</dd>
                  </div>
                  <div>
                    <dt className="text-xs uppercase tracking-[0.12em] text-[hsl(var(--muted-foreground))]">Warranty</dt>
                    <dd className="mt-1 text-sm text-[hsl(var(--foreground-strong))]">{formatDate(item.warranty_expiry)}</dd>
                  </div>
                  <div>
                    <dt className="text-xs uppercase tracking-[0.12em] text-[hsl(var(--muted-foreground))]">Current holder</dt>
                    <dd className="mt-1 text-sm text-[hsl(var(--foreground-strong))]">{item.current_assignee?.name || 'In stock'}</dd>
                  </div>
                </dl>
              </div>
            ))}
          </div>
        ) : (
          <EmptyState
            icon={BriefcaseBusiness}
            title="No assets match these filters"
            description="Adjust the current filters or add a new inventory item to populate the ledger."
          />
        )}
      </SectionCard>

      <div className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        <SectionCard title="Schedule maintenance" description="Queue preventative or repair work without losing sight of inventory status.">
          <form className="grid gap-4" onSubmit={handleScheduleMaintenance}>
            <div>
              <label className="field-label" htmlFor="maintenance-asset">
                Asset
              </label>
              <select
                id="maintenance-asset"
                className="field-input"
                value={maintenanceForm.asset}
                onChange={(event) => setMaintenanceForm((current) => ({ ...current, asset: event.target.value }))}
              >
                <option value="">Select asset</option>
                {items.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name} ({item.asset_tag || 'no tag'})
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="field-label" htmlFor="maintenance-type">
                Maintenance type
              </label>
              <input
                id="maintenance-type"
                className="field-input"
                value={maintenanceForm.maintenance_type}
                onChange={(event) => setMaintenanceForm((current) => ({ ...current, maintenance_type: event.target.value }))}
                placeholder="Screen replacement"
              />
            </div>
            <div>
              <label className="field-label" htmlFor="maintenance-date">
                Scheduled date
              </label>
              <input
                id="maintenance-date"
                type="date"
                className="field-input"
                value={maintenanceForm.scheduled_date}
                onChange={(event) => setMaintenanceForm((current) => ({ ...current, scheduled_date: event.target.value }))}
              />
            </div>
            <div>
              <label className="field-label" htmlFor="maintenance-vendor">
                Vendor
              </label>
              <input
                id="maintenance-vendor"
                className="field-input"
                value={maintenanceForm.vendor}
                onChange={(event) => setMaintenanceForm((current) => ({ ...current, vendor: event.target.value }))}
                placeholder="Authorized service partner"
              />
            </div>
            <button type="submit" className="btn-secondary" disabled={createMaintenanceMutation.isPending}>
              Schedule maintenance
            </button>
          </form>
        </SectionCard>

        <SectionCard title="Maintenance queue" description="Active and completed maintenance records across the current organisation inventory.">
          {maintenanceRecords.length ? (
            <div className="space-y-3">
              {maintenanceRecords.map((record) => (
                <div key={record.id} className="rounded-[20px] border border-[hsl(var(--border))] bg-white/70 px-4 py-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="font-semibold text-[hsl(var(--foreground-strong))]">{record.asset_name}</p>
                      <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">{record.maintenance_type}</p>
                    </div>
                    <StatusBadge tone={record.completed_date ? 'success' : 'warning'}>
                      {record.completed_date ? 'Completed' : 'Scheduled'}
                    </StatusBadge>
                  </div>
                  <p className="mt-3 text-sm text-[hsl(var(--muted-foreground))]">
                    Scheduled {formatDate(record.scheduled_date)}
                    {record.completed_date ? ` • Completed ${formatDate(record.completed_date)}` : ''}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState
              icon={Wrench}
              title="No maintenance scheduled"
              description="Schedule upkeep or repair work here to keep asset readiness visible."
            />
          )}
        </SectionCard>
      </div>
    </div>
  )
}
