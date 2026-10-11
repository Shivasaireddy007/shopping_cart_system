import './index.css'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { createBrowserRouter, RouterProvider } from 'react-router-dom'

import { Layout } from './components/Layout'
import { AdminProducts } from './pages/admin/AdminProducts'
import { ProductForm } from './pages/admin/ProductForm'
import { RequireAdmin } from './pages/admin/RequireAdmin'
import { LoginPage, RegisterPage } from './pages/AuthPages'
import { CartPage } from './pages/CartPage'
import { Catalog } from './pages/Catalog'
import { NotFound } from './pages/NotFound'
import { ProductPage } from './pages/ProductPage'

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 30_000, refetchOnWindowFocus: false } },
})

const router = createBrowserRouter([
  {
    element: <Layout />,
    children: [
      { path: '/', element: <Catalog /> },
      { path: '/p/:slug', element: <ProductPage /> },
      { path: '/cart', element: <CartPage /> },
      { path: '/login', element: <LoginPage /> },
      { path: '/register', element: <RegisterPage /> },
      {
        path: '/admin',
        element: <RequireAdmin />,
        children: [
          { index: true, element: <AdminProducts /> },
          { path: 'products/:id', element: <ProductForm /> },
        ],
      },
      { path: '*', element: <NotFound /> },
    ],
  },
])

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  </StrictMode>,
)
