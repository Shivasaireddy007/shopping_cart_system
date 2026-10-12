/** Set at build time for the public demo (VITE_DEMO_NOTICE); empty in normal builds. */
export const DEMO_NOTICE = (import.meta.env.VITE_DEMO_NOTICE as string | undefined) || undefined
export const IS_DEMO = Boolean(DEMO_NOTICE)
