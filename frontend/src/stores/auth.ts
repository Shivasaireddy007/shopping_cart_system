import { create } from 'zustand'
import { persist } from 'zustand/middleware'

type AuthState = {
  accessToken: string | null
  refreshToken: string | null
  setTokens: (tokens: { access_token: string; refresh_token: string }) => void
  logout: () => void
}

export const useAuth = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      refreshToken: null,
      setTokens: (tokens) => set({ accessToken: tokens.access_token, refreshToken: tokens.refresh_token }),
      logout: () => set({ accessToken: null, refreshToken: null }),
    }),
    { name: 'shopping-cart-auth' },
  ),
)
