import { describe, expect, it } from 'vitest'

import { addressSchema } from './address'

const valid = {
  name: 'Asha Rao',
  phone: '9876543210',
  line1: '12 MG Road',
  city: 'Bengaluru',
  state: 'Karnataka',
  pincode: '560001',
}

describe('addressSchema', () => {
  it('accepts a valid Indian address', () => {
    expect(addressSchema.safeParse(valid).success).toBe(true)
  })

  it.each([
    ['phone', '12345'],
    ['phone', '5876543210'],
    ['pincode', '056001'],
    ['pincode', '56001'],
    ['state', 'Atlantis'],
  ])('rejects %s = %s', (field, value) => {
    const result = addressSchema.safeParse({ ...valid, [field]: value })
    expect(result.success).toBe(false)
    expect(result.error?.issues[0].path).toEqual([field])
  })
})
