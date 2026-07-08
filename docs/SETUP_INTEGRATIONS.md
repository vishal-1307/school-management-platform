# Integrations Setup (Razorpay, WhatsApp, Cloudinary)

Each of these is optional — the platform runs without them and degrades clearly (disabled
buttons, 503s with readable messages, SKIPPED rows in the Communication Log).

## Razorpay (online fee payments)

1. Create an account at [razorpay.com](https://razorpay.com) → complete KYC with the school's
   details (needs the school's bank account, PAN, and a working website — the public site
   qualifies; note the Privacy Policy/Terms pages requirement).
2. **Settings → API Keys → Generate key** (start in Test Mode).
3. Render env vars: `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`.
4. **Settings → Webhooks** → add `https://<render-service>.onrender.com/api/fees/razorpay/webhook`,
   subscribe to `payment.captured`, and put the webhook secret in `RAZORPAY_WEBHOOK_SECRET`.
5. Test with Razorpay's test cards from the Student Portal → Fees → Pay Now, then switch to
   Live keys.

## WhatsApp Cloud API (parent messaging)

1. In [Meta for Developers](https://developers.facebook.com): create an app → add the
   **WhatsApp** product. You need a Meta Business account and a phone number for the school
   (cannot be a number already on the WhatsApp app).
2. From **WhatsApp → API Setup** copy:
   - Permanent access token → Render `WHATSAPP_TOKEN`
   - Phone number ID → Render `WHATSAPP_PHONE_ID`
3. Turn on the automations in Admin → Settings → Automation.

**Important — the 24-hour rule:** WhatsApp only allows free-form text messages to parents who
messaged the school within the last 24 hours. For cold notifications (absence alerts, fee
reminders) production use requires **pre-approved message templates**. The current build sends
text messages (fine for testing and for parents who have replied); before going live at scale,
create templates in Meta Business Manager and we can switch the automations to
`send_template_message` (the service already supports it).

## Cloudinary (photos & documents)

1. Create a free account at [cloudinary.com](https://cloudinary.com).
2. Dashboard → copy the **API Environment variable** (`cloudinary://key:secret@cloud`).
3. Render env var: `CLOUDINARY_URL`.
4. This enables direct uploads for gallery photos, homework attachments, and submissions via
   `GET /api/uploads/signature`.

## After adding any key

Render → Manual Deploy → "Deploy latest commit" (env changes need a restart).
