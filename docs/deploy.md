# Deploying the demo

The public demo runs on free tiers: the app on [Render](https://render.com), MySQL on
[Aiven](https://aiven.io) and Redis on [Upstash](https://upstash.com). Elasticsearch and
Shiprocket are turned off, so search uses its MySQL fallback and paid orders aren't shipped.
Razorpay runs in test mode, so no real money moves.

On every start the container runs migrations, sets up the storefront tables and seeds a
1,000-product catalog plus a demo customer if the database is empty (see
[`docker/entrypoint.sh`](../docker/entrypoint.sh)).

## 1. MySQL on Aiven

1. Sign up at https://console.aiven.io and create a **MySQL** service on the **Free** plan.
2. When it's running, open it and note **Host**, **Port**, **User** and **Password** from
   *Connection information*.
3. Download the **CA certificate** from the same page.

## 2. Redis on Upstash

1. Sign up at https://console.upstash.com and create a **Redis** database
   (region: Mumbai or Singapore).
2. Copy the connection URL that starts with `rediss://`.

## 3. Razorpay test keys

1. In the [Razorpay dashboard](https://dashboard.razorpay.com), switch to **Test mode**.
2. Go to *Account & Settings → API keys* and generate a key. Note the **Key Id** and **Key Secret**.

## 4. App key

Generate a Laravel app key locally:

```bash
php artisan key:generate --show
```

## 5. Render

1. Sign up at https://render.com with GitHub and choose **New → Blueprint**.
2. Pick this repository. Render reads [`render.yaml`](../render.yaml) and asks for the secret values:

| Setting | Value |
|---|---|
| `APP_KEY` | Output of step 4 (starts with `base64:`) |
| `APP_URL` | Leave blank for now |
| `DB_HOST`, `DB_PORT`, `DB_USERNAME`, `DB_PASSWORD` | From Aiven |
| `DB_CA_CERT` | Full contents of Aiven's CA certificate file |
| `REDIS_URL` | Upstash `rediss://` URL |
| `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET` | Razorpay test keys |

3. Click **Apply**. The first build takes around 10 minutes.
4. Copy the service URL (for example `https://shopping-cart-api.onrender.com`), set it as
   `APP_URL` under *Environment*, and save. Render redeploys automatically.

Open `<your URL>/docs/api` to see the live API docs.

## Notes

- Free Render services sleep after 15 minutes without traffic; the first request then takes
  about 30–60 seconds.
- Demo login: `demo@shoppingcart.test` / `demo-password`.
- To pay in the demo, use Razorpay's [test cards or UPI IDs](https://razorpay.com/docs/payments/payments/test-card-details/),
  for example UPI `success@razorpay`.
