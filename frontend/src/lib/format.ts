export function formatDate(value?: string | null) {
  if (!value) return 'Not set'
  return new Intl.DateTimeFormat('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  }).format(new Date(value))
}

export function formatDateTime(value?: string | null) {
  if (!value) return 'Not available'
  return new Intl.DateTimeFormat('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}

export function formatINR(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === '') return '₹0.00'
  const num = typeof value === 'string' ? parseFloat(value.replace(/,/g, '')) : value
  if (isNaN(num)) return '₹0.00'
  const formatted = new Intl.NumberFormat('en-IN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(Math.abs(num))
  return `${num < 0 ? '-' : ''}₹${formatted}`
}

export function startCase(value?: string | null) {
  if (!value) return 'Unknown'
  return value
    .toLowerCase()
    .split('_')
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(' ')
}
