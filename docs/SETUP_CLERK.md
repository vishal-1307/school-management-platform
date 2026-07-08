# Clerk Setup (real logins)

Until this is done, the platform runs in **DEV_AUTH demo mode**: the sign-in page shows a role
picker and anyone can enter any portal. That's for demoing only — do this setup before the school
enters real data.

## 1. Create the Clerk application

1. Sign up at [clerk.com](https://clerk.com) (free tier is fine for a pilot).
2. Create an application, e.g. "Knowledge Academy".
3. In **User & Authentication → Email, Phone, Username**:
   - Enable **Username** and **Password**.
   - Make **Email** optional (students sign in with their admission number as username — most
     have no email).

## 2. Session token (role claim for fast routing)

In **Sessions → Customize session token**, add:

```json
{ "metadata": "{{user.public_metadata}}" }
```

This lets the frontend route users to the right portal without an extra API call. (The backend
still independently verifies the role on every request — this is a convenience, not the security
boundary.)

## 3. Copy the keys

From **API Keys**:

| Key | Goes to |
|---|---|
| Publishable key (`pk_…`) | Vercel → `PUBLIC_CLERK_PUBLISHABLE_KEY` |
| Secret key (`sk_…`) | Render → `CLERK_SECRET_KEY` **and** Vercel → `CLERK_SECRET_KEY` |
| Frontend API URL (e.g. `https://xxx.clerk.accounts.dev`) | Render → `CLERK_ISSUER` |
| JWKS URL (`{issuer}/.well-known/jwks.json`) | Render → `CLERK_JWKS_URL` (optional — derived from issuer if unset) |

## 4. Webhook (keeps local users in sync)

1. Clerk **Webhooks → Add endpoint**: `https://<your-render-service>.onrender.com/api/webhooks/clerk`
2. Subscribe to `user.updated` and `user.deleted`.
3. Copy the signing secret (`whsec_…`) → Render → `CLERK_WEBHOOK_SECRET`.

## 5. Turn off demo mode

- Render: **delete** the `DEV_AUTH` env var (or set it to `false`).
- Vercel: add `PUBLIC_CLERK_PUBLISHABLE_KEY` + `CLERK_SECRET_KEY` (step 3) and **delete**
  `PUBLIC_DEV_AUTH`.
- Redeploy both services. The sign-in page switches from the role picker to real Clerk login
  automatically.

## 6. Link existing users

Any users created while Clerk was unconfigured show as **Pending** in Admin → Users & Roles.
For each: click through the provision flow (set username/password) — this creates the real
Clerk account and links it. New users created from now on are provisioned automatically.

The seeded `pending:super-admin` user is your own login: provision it first (email + password),
then sign in at `/sign-in`.

## How auth works after setup

- Clerk issues RS256 session tokens; the backend verifies them against Clerk's JWKS and looks up
  the local user by `clerk_id` for the authoritative role and record links.
- Roles: `super_admin`, `office_admin`, `teacher`, `student` (parents share the student login).
- Deactivating a user in Admin → Users bans them in Clerk immediately.
