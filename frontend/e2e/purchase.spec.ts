import { expect, type Page, test } from '@playwright/test'

/** Must match RAZORPAY_KEY_SECRET of the stack under test (docker-compose.e2e.yml). */
const RAZORPAY_SECRET = process.env.E2E_RAZORPAY_SECRET ?? 'e2e-razorpay-secret'

/**
 * Stands in for Razorpay Checkout's script: "pays" immediately and signs the result with the
 * test secret, exactly as Razorpay would, so the backend's signature check runs for real.
 */
async function fakeRazorpayCheckout(page: Page) {
  await page.route('https://checkout.razorpay.com/**', (route) =>
    route.fulfill({
      contentType: 'application/javascript',
      body: `
        window.Razorpay = function (options) {
          this.open = async () => {
            const paymentId = 'pay_' + Math.random().toString(16).slice(2, 16)
            const key = await crypto.subtle.importKey('raw', new TextEncoder().encode(${JSON.stringify(RAZORPAY_SECRET)}),
              { name: 'HMAC', hash: 'SHA-256' }, false, ['sign'])
            const signature = await crypto.subtle.sign('HMAC', key, new TextEncoder().encode(options.order_id + '|' + paymentId))
            const hex = [...new Uint8Array(signature)].map((b) => b.toString(16).padStart(2, '0')).join('')
            options.handler({ razorpay_payment_id: paymentId, razorpay_order_id: options.order_id, razorpay_signature: hex })
          }
        }`,
    }),
  )
}

test('a shopper finds a product, pays and sees it shipped', async ({ page }) => {
  await fakeRazorpayCheckout(page)
  const email = `shopper-${Date.now()}@example.com`

  await test.step('register', async () => {
    await page.goto('/register')
    await page.getByLabel('Name').fill('Asha Rao')
    await page.getByLabel('Email').fill(email)
    await page.getByLabel('Password').fill('a-strong-password')
    await page.getByRole('button', { name: 'Create account' }).click()
    await expect(page.getByRole('button', { name: 'Sign out' })).toBeVisible()
  })

  await test.step('search and add an in-stock product to the cart', async () => {
    await page.getByRole('searchbox', { name: 'Search products' }).fill('running shoes')
    await page.getByRole('searchbox', { name: 'Search products' }).press('Enter')
    await expect(page.getByRole('heading', { name: /Results for “running shoes”/ })).toBeVisible()
    // The filter lives in the URL, so the box ticks once navigation settles.
    await page.getByLabel('In stock only').click()
    await expect(page.getByLabel('In stock only')).toBeChecked()
    await expect(page).toHaveURL(/in_stock=true/)
    await page.locator('main a[href^="/p/"]').first().click()
    await page.getByRole('button', { name: 'Add to cart' }).click()
    await expect(page.getByText('Added to your cart')).toBeVisible()
  })

  await test.step('check out and pay', async () => {
    await page.getByRole('link', { name: 'View cart' }).click()
    await page.getByRole('link', { name: 'Checkout' }).click()
    await page.getByLabel('Full name').fill('Asha Rao')
    await page.getByLabel('Mobile number').fill('9876543210')
    await page.getByLabel('Flat, house, street').fill('12, 4th Cross, MG Road')
    await page.getByLabel('City').fill('Bengaluru')
    await page.getByLabel('PIN code').fill('560001')
    await page.getByLabel('State').selectOption('Karnataka')
    await page.getByRole('button', { name: /^Pay ₹/ }).click()

    await expect(page).toHaveURL(/\/orders\/ORD-/)
    await expect(page.getByRole('heading', { name: 'Thank you for your order' })).toBeVisible()
  })

  await test.step('the order ships through Kafka and Shiprocket', async () => {
    // order.paid -> outbox -> relay -> Kafka -> shipping worker -> Shiprocket -> courier assigned
    await expect(async () => {
      await page.reload()
      await expect(page.getByText('Delhivery', { exact: true })).toBeVisible({ timeout: 1_000 })
    }).toPass({ timeout: 45_000 })
    await expect(page.getByText('In transit · Bengaluru hub')).toBeVisible()
  })

  await test.step('the order appears in history', async () => {
    await page.getByRole('link', { name: 'Orders' }).click()
    await expect(page.getByRole('heading', { name: 'Your orders' })).toBeVisible()
    await expect(page.locator('main li').first()).toContainText('Paid')
  })
})
