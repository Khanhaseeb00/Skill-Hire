# Kaamgar Backend

Real, runnable Flask + SQLite backend for the daily-wage hiring app —
tested end-to-end on a live local server. Two connected frontends, one
Flask app:

- **`/`** — hirer dashboard: browse/search workers, hire, pay via Razorpay, message, track status
- **`/worker`** — worker portal: see assigned jobs, real GPS check-in, message the hirer, upload ID for verification

## Setup

```bash
pip install -r requirements.txt
python seed_data.py      # one-time: loads 9 sample workers, all logged into /worker with password "kaamgar123"
python app.py            # starts on http://localhost:5000
```

Open **http://localhost:5000** for the hirer dashboard, and
**http://localhost:5000/worker** for the worker portal (open this on your
phone, or desktop Chrome/Firefox, to test real GPS — see below).

## What's real vs. what needs your own account

**Real and tested end-to-end against a running server:**
- Full auth for both hirers and workers (separate logins, hashed passwords)
- Booking lifecycle: `requested → confirmed → en_route → checked_in → in_progress → completed`,
  gated so a worker can't advance status until the hirer has actually paid
- **Razorpay payments** — order creation, checkout-signature verification,
  and webhook-signature verification (tested with real HMAC signatures over the wire)
- **Real GPS location tracking** — the worker portal calls the browser's
  `navigator.geolocation` API and sends the actual coordinates; the backend
  checks the caller is the worker assigned to that specific booking
- **In-app messaging** between hirer and worker, scoped per booking, access-controlled
- **ID verification workflow** — worker uploads a photo/PDF, an admin
  approves or rejects it via an admin-key-protected endpoint

**Needs your own third-party account (can't be tested from an offline sandbox):**
- **SMS notifications** (`notifications.py`) — uses Twilio's API. Every
  `notify()` call is wrapped so a missing/failed SMS never breaks the
  booking/payment/status flow itself — it's a side effect, not a dependency.

**Honest limitation, by design, not a bug:**
- ID verification is a **manual review workflow**, not a live government
  database check. A real Aadhaar/DigiLocker API integration requires a
  registered business entity and UIDAI approval — most platforms start
  exactly here and add the automated check once they have that approval.

## Razorpay setup (test mode — no business verification needed)

1. Sign up at https://dashboard.razorpay.com and switch to **Test Mode** (toggle top-left).
2. **Settings > API Keys > Generate Test Key** — copy the Key ID and Key Secret.
3. Copy `.env.example` to `.env` and fill in the values, or export them directly:
   ```bash
   export RAZORPAY_KEY_ID=rzp_test_xxxxxxxx
   export RAZORPAY_KEY_SECRET=xxxxxxxxxxxxxxxx
   ```
4. Restart `python app.py`.
5. Create a booking, open `http://localhost:5000/checkout/<booking_id>`,
   click **Pay with Razorpay**, use test card `4111 1111 1111 1111` (any
   future expiry, any CVV) — full list at
   https://razorpay.com/docs/payments/payments/test-card-upi-details/
6. On success the booking flips to `confirmed` / `payment_status: paid`,
   and the worker's check-in button unlocks in `/worker`.

### Webhook (don't skip this before a real launch)

The webhook confirms payment even if the browser closes right after paying.

1. Local testing: `ngrok http 5000` (or `cloudflared tunnel --url http://localhost:5000`)
2. Razorpay Dashboard > **Settings > Webhooks** > Add webhook:
   URL `https://<your-ngrok-domain>/api/payments/webhook`, event `payment.captured`,
   set a secret → paste into `RAZORPAY_WEBHOOK_SECRET`.
3. Restart, make a test payment, check the webhook logs in the dashboard for a `200`.

In production, point this at your real deployed domain instead of ngrok.

## SMS notifications (Twilio — optional)

The app works fully without this; SMS is just a nice-to-have layered on top.

1. Free trial at https://twilio.com — gives you a real number + credits, no card needed to start.
2. Copy the Account SID, Auth Token, and your Twilio phone number into `.env`.
3. Restart the server. SMS now fires on: booking confirmed (to both sides),
   new chat message, worker GPS status update, and ID verification result.
4. Trial accounts can only text numbers you've verified in the Twilio
   console — fine for testing, upgrade the account before real users.

## Testing real GPS locally

`navigator.geolocation` requires a "secure context" — `https://` or
`localhost` specifically. Opening `http://localhost:5000/worker` in a
browser on the **same computer running the server** works fine. To test
from an actual phone, use `ngrok http 5000` and open the `https://` ngrok
URL on the phone (plain `http://192.168.x.x:5000` will NOT get location
permission, since it isn't `localhost` or HTTPS).

## Admin: reviewing ID verification

```bash
# See who's waiting for review
curl "http://localhost:5000/api/admin/workers/pending?admin_key=YOUR_ADMIN_KEY"

# Approve or reject
curl -X POST "http://localhost:5000/api/admin/workers/3/verify?admin_key=YOUR_ADMIN_KEY" \
  -H "Content-Type: application/json" -d '{"approve": true}'
```
Set `ADMIN_KEY` in `.env` to any long random string first — these routes
refuse to work at all without it.

## Deploying (Render, free tier)

This puts the app on a real public URL — needed for Razorpay's webhook and
for anyone besides you to open it.

1. Push this folder to a GitHub repo (make sure `.env` is **not** committed —
   `.gitignore` already excludes it).
2. Go to https://render.com > **New > Blueprint**, connect the repo. Render
   reads `render.yaml` in this project and sets up the service, a persistent
   1GB disk (for the SQLite file and uploaded ID photos — otherwise both
   vanish on every redeploy), and build/start commands automatically.
3. In the Render dashboard, fill in the environment variables it left
   blank: `ADMIN_KEY`, `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`,
   `RAZORPAY_WEBHOOK_SECRET`, and the `TWILIO_*` ones if you're using SMS.
4. Deploy. Render gives you a URL like `https://kaamgar-backend.onrender.com`
   — that's your real, live app. Update the Razorpay webhook URL to point
   here instead of ngrok.
5. Free tier note: the service sleeps after inactivity and takes ~30s to
   wake on the next request. Fine for testing/demoing; upgrade the plan
   before relying on it for real users.

No Procfile changes needed — `gunicorn` (a production-grade server, unlike
Flask's built-in dev server) is already in `requirements.txt` and wired up
in both `Procfile` and `render.yaml`.

## API reference

| Method | Path                                     | Purpose                                       |
|--------|-------------------------------------------|------------------------------------------------|
| POST   | `/api/auth/register` / `/login` / `/logout` | Hirer auth                                   |
| GET    | `/api/auth/me`                            | Check hirer session                            |
| POST   | `/api/worker-auth/register` / `/login` / `/logout` | Worker auth (separate from hirers)     |
| GET    | `/api/worker-auth/me`                     | Check worker session                           |
| GET    | `/api/workers?skill=&city=&q=`            | Search workers                                 |
| GET    | `/api/workers/<id>`                       | One worker's profile                           |
| POST   | `/api/bookings`                           | Create a booking                               |
| POST   | `/api/bookings/<id>/create-order`         | Create Razorpay order                          |
| GET    | `/checkout/<id>`                          | Test page — opens Razorpay Checkout            |
| POST   | `/api/payments/verify`                    | Verify checkout signature, mark paid           |
| POST   | `/api/payments/webhook`                   | Razorpay webhook (`payment.captured`)          |
| GET    | `/api/bookings`                           | Hirer's own bookings                           |
| POST   | `/api/bookings/<id>/advance-status`       | Hirer-side manual status advance (payment-gated) |
| GET    | `/api/bookings/<id>/events`               | Full status/location history                   |
| GET    | `/api/worker/bookings`                    | Worker's assigned bookings                     |
| POST   | `/api/worker/bookings/<id>/check-in`      | **Real GPS** check-in (payment-gated, worker-only) |
| GET/POST | `/api/bookings/<id>/messages`           | Read/send chat, access-controlled per booking  |
| POST   | `/api/worker/verification/upload`         | Worker uploads ID document                     |
| GET    | `/api/admin/workers/pending`              | Admin: list workers awaiting review            |
| POST   | `/api/admin/workers/<id>/verify`          | Admin: approve/reject                          |

## Next steps, roughly in order

1. Input validation hardening — currently minimal, don't expose this to
   real strangers on the internet as-is
2. Move SQLite → Postgres for real concurrent users (see below)
3. Ratings/reviews, filed after a booking reaches `completed`
4. Move from Twilio to an India-focused SMS gateway (MSG91 etc.) if SMS
   volume gets meaningful — usually cheaper per message
5. Before accepting real money: switch Razorpay from Test to Live keys and
   complete their KYC/business verification (required, not optional)
6. Real Aadhaar/DigiLocker verification API once you have a registered
   business entity and UIDAI approval

## Moving to Postgres later

Everything routes through `db.py`'s `get_db()`. Swap that function's body
for a `psycopg2.connect(...)` call, change `schema.sql`'s `AUTOINCREMENT` to
`SERIAL PRIMARY KEY`, and nothing else needs to change — the SQL used
throughout this project is plain, portable SQL.
