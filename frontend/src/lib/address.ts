import { z } from 'zod'

import { INDIAN_STATES } from './states'

export const addressSchema = z.object({
  name: z.string().trim().min(1, 'Enter the recipient’s name').max(100),
  phone: z.string().trim().regex(/^[6-9]\d{9}$/, 'Enter a 10-digit mobile number'),
  line1: z.string().trim().min(1, 'Enter the address').max(255),
  line2: z.string().trim().max(255).optional(),
  city: z.string().trim().min(1, 'Enter the city').max(100),
  state: z.enum(INDIAN_STATES, { error: 'Choose a state' }),
  pincode: z.string().trim().regex(/^[1-9]\d{5}$/, 'Enter a 6-digit PIN code'),
})
