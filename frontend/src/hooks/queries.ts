import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api, type Cart, type ProductCreate, unwrap } from '../api/client'
import type { paths } from '../api/schema'
import { useAuth } from '../stores/auth'

export type ProductQuery = NonNullable<paths['/api/v1/products']['get']['parameters']['query']>

export function useCategories() {
  return useQuery({
    queryKey: ['categories'],
    queryFn: () => unwrap(api.GET('/api/v1/categories')),
    staleTime: 5 * 60_000,
  })
}

export function useProducts(query: ProductQuery) {
  return useQuery({
    queryKey: ['products', query],
    queryFn: () => unwrap(api.GET('/api/v1/products', { params: { query } })),
    placeholderData: keepPreviousData,
  })
}

export function useProduct(slug: string) {
  return useQuery({
    queryKey: ['product', slug],
    queryFn: () => unwrap(api.GET('/api/v1/products/{slug}', { params: { path: { slug } } })),
  })
}

export function useMe() {
  const token = useAuth((s) => s.accessToken)
  return useQuery({
    queryKey: ['me', token],
    queryFn: () => unwrap(api.GET('/api/v1/auth/me')),
    enabled: token !== null,
    retry: false,
  })
}

export function useCart() {
  const token = useAuth((s) => s.accessToken)
  return useQuery({
    queryKey: ['cart'],
    queryFn: () => unwrap(api.GET('/api/v1/cart')),
    enabled: token !== null,
  })
}

/** Cart changes return the whole cart, so the cache is replaced instead of refetched. */
function useCartMutation<TVars>(fn: (vars: TVars) => Promise<Cart>) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: fn,
    onSuccess: (cart) => client.setQueryData(['cart'], cart),
  })
}

export const useAddToCart = () =>
  useCartMutation((vars: { productId: number; quantity: number }) =>
    unwrap(api.POST('/api/v1/cart/items', { body: { product_id: vars.productId, quantity: vars.quantity } })),
  )

export const useUpdateCartItem = () =>
  useCartMutation((vars: { itemId: number; quantity: number }) =>
    unwrap(
      api.PATCH('/api/v1/cart/items/{item_id}', {
        params: { path: { item_id: vars.itemId } },
        body: { quantity: vars.quantity },
      }),
    ),
  )

export const useRemoveCartItem = () =>
  useCartMutation((itemId: number) =>
    unwrap(api.DELETE('/api/v1/cart/items/{item_id}', { params: { path: { item_id: itemId } } })),
  )

export function useAdminProducts(search: string, page: number) {
  return useQuery({
    queryKey: ['admin-products', search, page],
    queryFn: () =>
      unwrap(api.GET('/api/v1/admin/products', { params: { query: { search: search || undefined, page } } })),
    placeholderData: keepPreviousData,
  })
}

export function useSaveProduct() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (vars: { id?: number; body: ProductCreate }) =>
      vars.id
        ? unwrap(api.PATCH('/api/v1/admin/products/{product_id}', { params: { path: { product_id: vars.id } }, body: vars.body }))
        : unwrap(api.POST('/api/v1/admin/products', { body: vars.body })),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ['admin-products'] })
      void client.invalidateQueries({ queryKey: ['products'] })
    },
  })
}

export function useArchiveProduct() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (id: number) =>
      unwrap(api.DELETE('/api/v1/admin/products/{product_id}', { params: { path: { product_id: id } } })),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ['admin-products'] })
      void client.invalidateQueries({ queryKey: ['products'] })
    },
  })
}
