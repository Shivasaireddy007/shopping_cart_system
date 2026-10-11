import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import { z } from 'zod'

import type { Product } from '../../api/client'
import { useCategories, useSaveProduct } from '../../hooks/queries'

/** Prices are typed in rupees and sent in paise. */
const schema = z
  .object({
    name: z.string().trim().min(1, 'Enter a name').max(255),
    sku: z.string().trim().regex(/^[A-Za-z0-9_-]+$/, 'Letters, numbers, - and _ only').max(64),
    brand: z.string().trim().min(1, 'Enter a brand').max(100),
    category_id: z.coerce.number<string>().int().positive('Pick a category'),
    price: z.coerce.number<string>().min(1, 'At least ₹1'),
    mrp: z.union([z.literal(''), z.coerce.number<string>().min(1)]).optional(),
    stock: z.coerce.number<string>().int().min(0, "Stock can't be negative"),
    description: z.string().max(5000).optional(),
    color: z.string().max(50).optional(),
    size: z.string().max(20).optional(),
  })
  .refine((v) => v.mrp === undefined || v.mrp === '' || v.mrp >= v.price, {
    path: ['mrp'],
    message: 'MRP must be at least the price',
  })

type FormInput = z.input<typeof schema>
type FormOutput = z.output<typeof schema>

export function ProductForm() {
  const { id } = useParams()
  const existing = (useLocation().state as { product?: Product } | null)?.product
  const editing = id !== undefined && id !== 'new'
  const navigate = useNavigate()
  const { data: categories } = useCategories()
  const save = useSaveProduct()

  const form = useForm<FormInput, unknown, FormOutput>({
    resolver: zodResolver(schema),
    defaultValues: existing
      ? {
          name: existing.name,
          sku: existing.sku,
          brand: existing.brand,
          category_id: String(existing.category.id),
          price: String(existing.price / 100),
          mrp: existing.mrp ? String(existing.mrp / 100) : '',
          stock: String(existing.stock),
          description: existing.description ?? '',
          color: String(existing.attributes.color ?? ''),
          size: String(existing.attributes.size ?? ''),
        }
      : { category_id: '', price: '', stock: '0', mrp: '' },
  })

  // The category <select> can only show the saved value once its options exist.
  if (!categories) return <p className="text-muted">Loading…</p>

  if (editing && !existing) {
    return (
      <p className="rounded-lg bg-surface p-6">
        Open products from the <Link to="/admin" className="font-semibold text-brand">products list</Link> to edit them.
      </p>
    )
  }

  const onSubmit = form.handleSubmit(async (v) => {
    try {
      await save.mutateAsync({
        id: editing ? Number(id) : undefined,
        body: {
          name: v.name,
          sku: v.sku,
          brand: v.brand,
          category_id: v.category_id,
          price: Math.round(v.price * 100),
          mrp: v.mrp === '' || v.mrp === undefined ? null : Math.round(v.mrp * 100),
          stock: v.stock,
          description: v.description || null,
          attributes: { color: v.color || null, size: v.size || null },
        },
      })
      navigate('/admin')
    } catch (error) {
      form.setError('root', { message: error instanceof Error ? error.message : 'Could not save' })
    }
  })

  const err = form.formState.errors
  const input = 'rounded-lg border border-line bg-surface px-3 py-2 aria-invalid:border-crit'

  return (
    <form onSubmit={onSubmit} noValidate className="grid max-w-2xl gap-4 rounded-xl bg-surface p-6">
      <h1 className="text-2xl font-extrabold">{editing ? 'Edit product' : 'New product'}</h1>
      <div className="grid gap-4 sm:grid-cols-2">
        <Labeled id="name" label="Name" error={err.name?.message} className="sm:col-span-2">
          <input id="name" className={input} aria-invalid={!!err.name} {...form.register('name')} />
        </Labeled>
        <Labeled id="sku" label="SKU" error={err.sku?.message}>
          <input id="sku" className={`${input} font-mono`} aria-invalid={!!err.sku} {...form.register('sku')} />
        </Labeled>
        <Labeled id="category_id" label="Category" error={err.category_id?.message}>
          <select id="category_id" className={input} aria-invalid={!!err.category_id} {...form.register('category_id')}>
            <option value="">Choose…</option>
            {categories?.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        </Labeled>
        <Labeled id="brand" label="Brand" error={err.brand?.message}>
          <input id="brand" className={input} aria-invalid={!!err.brand} {...form.register('brand')} />
        </Labeled>
        <Labeled id="stock" label="Stock" error={err.stock?.message}>
          <input id="stock" type="number" min={0} className={`${input} tabular`} aria-invalid={!!err.stock} {...form.register('stock')} />
        </Labeled>
        <Labeled id="price" label="Price (₹)" error={err.price?.message}>
          <input id="price" type="number" min={1} step="0.01" className={`${input} tabular`} aria-invalid={!!err.price} {...form.register('price')} />
        </Labeled>
        <Labeled id="mrp" label="MRP (₹, optional)" error={err.mrp?.message}>
          <input id="mrp" type="number" min={1} step="0.01" className={`${input} tabular`} aria-invalid={!!err.mrp} {...form.register('mrp')} />
        </Labeled>
        <Labeled id="color" label="Colour" error={err.color?.message}>
          <input id="color" className={input} {...form.register('color')} />
        </Labeled>
        <Labeled id="size" label="Size" error={err.size?.message}>
          <input id="size" className={input} {...form.register('size')} />
        </Labeled>
        <Labeled id="description" label="Description" error={err.description?.message} className="sm:col-span-2">
          <textarea id="description" rows={4} className={input} {...form.register('description')} />
        </Labeled>
      </div>
      {err.root ? <p role="alert" className="rounded-lg bg-crit-soft px-3 py-2 text-crit">{err.root.message}</p> : null}
      <div className="flex gap-3">
        <button type="submit" disabled={form.formState.isSubmitting} className="rounded-lg bg-brand px-5 py-2.5 font-semibold text-white hover:bg-brand-dark disabled:opacity-60">
          {form.formState.isSubmitting ? 'Saving…' : editing ? 'Save changes' : 'Create product'}
        </button>
        <Link to="/admin" className="rounded-lg border border-line px-5 py-2.5 font-semibold">Cancel</Link>
      </div>
    </form>
  )
}

function Labeled(props: { id: string; label: string; error?: string; className?: string; children: React.ReactNode }) {
  return (
    <div className={`grid gap-1 ${props.className ?? ''}`}>
      <label htmlFor={props.id} className="text-sm font-semibold">{props.label}</label>
      {props.children}
      {props.error ? <p className="text-sm text-crit">{props.error}</p> : null}
    </div>
  )
}
