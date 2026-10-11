const STYLES: Record<string, { label: string; className: string }> = {
  pending_payment: { label: 'Awaiting payment', className: 'bg-warn-soft text-warn' },
  paid: { label: 'Paid', className: 'bg-good-soft text-good' },
  shipped: { label: 'Shipped', className: 'bg-good-soft text-good' },
  delivered: { label: 'Delivered', className: 'bg-good-soft text-good' },
  cancelled: { label: 'Cancelled', className: 'bg-surface-2 text-muted' },
}

export function OrderStatus({ status }: { status: string }) {
  const style = STYLES[status] ?? { label: status, className: 'bg-surface-2 text-muted' }
  return <span className={`rounded-full px-2.5 py-1 text-xs font-semibold whitespace-nowrap ${style.className}`}>{style.label}</span>
}
