import { zodResolver } from '@hookform/resolvers/zod'
import { useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { z } from 'zod'

import { api, unwrap } from '../api/client'
import { Logo } from '../components/Logo'
import { useAuth } from '../stores/auth'

const loginSchema = z.object({
  email: z.email('Enter a valid email address'),
  password: z.string().min(1, 'Enter your password'),
})

const registerSchema = z.object({
  name: z.string().trim().min(1, 'Enter your name').max(100),
  email: z.email('Enter a valid email address'),
  password: z.string().min(8, 'Use at least 8 characters'),
})

type LoginValues = z.infer<typeof loginSchema>
type RegisterValues = z.infer<typeof registerSchema>

function useSignIn() {
  const setTokens = useAuth((s) => s.setTokens)
  const client = useQueryClient()
  const navigate = useNavigate()
  const from = (useLocation().state as { from?: string } | null)?.from ?? '/'

  return (tokens: { access_token: string; refresh_token: string }) => {
    setTokens(tokens)
    void client.invalidateQueries()
    navigate(from, { replace: true })
  }
}

export function LoginPage() {
  const signIn = useSignIn()
  const form = useForm<LoginValues>({ resolver: zodResolver(loginSchema) })

  const onSubmit = form.handleSubmit(async (values) => {
    try {
      signIn(await unwrap(api.POST('/api/v1/auth/login', { body: values })))
    } catch (error) {
      form.setError('root', { message: error instanceof Error ? error.message : 'Sign-in failed' })
    }
  })

  return (
    <AuthCard title="Sign in" footer={<>New here? <Link to="/register" className="font-semibold text-brand">Create an account</Link></>}>
      <form onSubmit={onSubmit} noValidate className="grid gap-4">
        <Field id="email" label="Email" type="email" autoComplete="email" error={form.formState.errors.email?.message} {...form.register('email')} />
        <Field id="password" label="Password" type="password" autoComplete="current-password" error={form.formState.errors.password?.message} {...form.register('password')} />
        {form.formState.errors.root ? <p role="alert" className="text-sm text-crit">{form.formState.errors.root.message}</p> : null}
        <button type="submit" disabled={form.formState.isSubmitting} className="rounded-lg bg-brand px-4 py-2.5 font-semibold text-white hover:bg-brand-dark disabled:opacity-60">
          {form.formState.isSubmitting ? 'Signing in…' : 'Sign in'}
        </button>
        <p className="text-xs text-muted">Demo login: demo@example.com / demo-password</p>
      </form>
    </AuthCard>
  )
}

export function RegisterPage() {
  const signIn = useSignIn()
  const form = useForm<RegisterValues>({ resolver: zodResolver(registerSchema) })

  const onSubmit = form.handleSubmit(async (values) => {
    try {
      signIn(await unwrap(api.POST('/api/v1/auth/register', { body: values })))
    } catch (error) {
      form.setError('root', { message: error instanceof Error ? error.message : 'Sign-up failed' })
    }
  })

  return (
    <AuthCard title="Create an account" footer={<>Already have one? <Link to="/login" className="font-semibold text-brand">Sign in</Link></>}>
      <form onSubmit={onSubmit} noValidate className="grid gap-4">
        <Field id="name" label="Name" autoComplete="name" error={form.formState.errors.name?.message} {...form.register('name')} />
        <Field id="email" label="Email" type="email" autoComplete="email" error={form.formState.errors.email?.message} {...form.register('email')} />
        <Field id="password" label="Password" type="password" autoComplete="new-password" error={form.formState.errors.password?.message} {...form.register('password')} />
        {form.formState.errors.root ? <p role="alert" className="text-sm text-crit">{form.formState.errors.root.message}</p> : null}
        <button type="submit" disabled={form.formState.isSubmitting} className="rounded-lg bg-brand px-4 py-2.5 font-semibold text-white hover:bg-brand-dark disabled:opacity-60">
          {form.formState.isSubmitting ? 'Creating account…' : 'Create account'}
        </button>
      </form>
    </AuthCard>
  )
}

function AuthCard({ title, footer, children }: { title: string; footer: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="mx-auto mt-6 grid max-w-sm gap-5 rounded-xl bg-surface p-6 shadow-sm">
      <Logo />
      <h1 className="text-2xl font-extrabold">{title}</h1>
      {children}
      <p className="text-sm text-muted">{footer}</p>
    </div>
  )
}

type FieldProps = React.InputHTMLAttributes<HTMLInputElement> & { id: string; label: string; error?: string }

function Field({ id, label, error, ...input }: FieldProps & { ref?: React.Ref<HTMLInputElement> }) {
  return (
    <div className="grid gap-1">
      <label htmlFor={id} className="text-sm font-semibold">{label}</label>
      <input
        id={id}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? `${id}-error` : undefined}
        className="rounded-lg border border-line bg-surface px-3 py-2 aria-invalid:border-crit"
        {...input}
      />
      {error ? <p id={`${id}-error`} className="text-sm text-crit">{error}</p> : null}
    </div>
  )
}
