# Public demo

The whole stack (PostgreSQL, Redis, OpenSearch, Kafka, the API, workers and web app) on one
Ubuntu server, behind [Caddy](https://caddyserver.com) for automatic HTTPS. Payments use Razorpay
**test mode**; shipping uses the Shiprocket stand-in, because Shiprocket only signs up registered
businesses. Demo data resets every night at 03:00 IST.

CI runs [`setup.sh`](setup.sh) on a fresh machine on every push, so these steps stay working.

## 1. Get a server

Any Ubuntu 22.04/24.04 server with **4 GB RAM or more** and ports 80 and 443 open works.
[Oracle Cloud's Always Free tier](https://www.oracle.com/cloud/free/) covers it at no cost:

1. Sign up (a card is needed for verification; Always Free resources aren't charged). Pick
   **India South (Hyderabad)** or **India West (Mumbai)** as the home region.
2. **Compute → Instances → Create instance**
   - Image: **Canonical Ubuntu 24.04**
   - Shape: **Ampere VM.Standard.A1.Flex**, 2 OCPUs, 12 GB memory
   - Save the SSH private key it offers
   - If it says "out of capacity", try another availability domain or try again later.
3. Open the instance's subnet → **Default security list → Add ingress rules**: source
   `0.0.0.0/0`, TCP, destination ports `80,443`.

## 2. Get Razorpay test keys

Sign up at [dashboard.razorpay.com](https://dashboard.razorpay.com), switch to **Test mode**, and
generate keys under **Account & Settings → API keys**. Test mode needs no business verification.

## 3. Run the setup script

```bash
ssh -i <key-file> ubuntu@<server-ip>
git clone https://github.com/Shivasaireddy007/shopping_cart_system.git
cd shopping_cart_system && sudo deploy/demo/setup.sh
```

It asks for a domain (press Enter to use the free `<ip>.sslip.io` name) and the Razorpay keys,
then installs Docker, builds and starts everything, loads demo data and schedules the jobs. The
first run takes about ten minutes. It finishes by printing the URL.

## Day to day

```bash
deploy/demo/compose.sh ps                         # what's running
deploy/demo/compose.sh logs -f api                # logs
git pull && deploy/demo/compose.sh up -d --build  # deploy the latest code
sudo deploy/demo/reset.sh                         # reset the data now
```
