# ERP alert when a customer taps "I have sent the money"

Written for: the engineers shipping this change across the three repos.

When a customer declares a bank transfer, the ERP now tells the staff who can confirm it, in-app and by
email. Before this, nobody was told and Finance had to refresh the funding list.

Branch `feat/funding-intent-notification` exists in all three repos. **Nothing is committed yet.**

| Repo | Stack | Based on | Role |
|---|---|---|---|
| `xbanka-web-app-backend` (core) | NestJS, Prisma | `pre-production` | Detects the declared intent and tells the ERP |
| `Xbanka-backend` (ERP backend) | FastAPI, SQLAlchemy, Alembic | `main` | Receives it, notifies staff, clears the alert |
| `xbankaAdmin` (ERP frontend) | Next.js | `main` | Shows the notification and links to the funding list |

## Highlights

- **Audience is decided by permission, not role.** Anyone holding at least one of
  `finance:adjust_balance`, `finance:approve_payments`, `finance:reject_payments` is notified, once each.
  This reuses the ERP's existing resolution (role defaults plus per-user overrides), so **Super Admin is
  included** because it holds every permission.
- **Always emailed.** Stored staff notification preferences are not read, so the email goes out even if a
  staff member switched email off. (The ERP stores those preferences but nothing enforces them yet.)
- **Best effort on the core side.** The call is not awaited, times out at 5 seconds and never throws. An
  ERP outage, wrong key or missing config is logged and the customer's request is unaffected.
- **Idempotent.** The ERP keys on the core transaction id, so a retried call notifies nobody twice.
- **The alert clears itself.** Completing or rejecting the intent in the ERP marks its notifications
  RESOLVED.
- **One shared secret, both directions.** The same key the ERP already uses to call the core now also
  authenticates the core calling the ERP.

## How it flows

```
Customer taps "I have sent"
  -> core: recordBankTransferIntent saves a PENDING intent
  -> core: POST {ERP_BASE_URL}/api/internal/funding-intents/declared   (x-internal-key, not awaited)
       -> ERP: key check, idempotency check
       -> ERP: find holders of any of the 3 permissions (deduped)
       -> ERP: one Notification row each (FUNDING_INTENT) + websocket push
       -> ERP: one email each, queued in the background
Staff clicks the bell or the email
  -> ERP frontend: /finance?tab=funding (Funding Requests tab, Pending list)
Staff Confirms or Rejects there
  -> ERP calls core /internal/funding/intents/:id/complete|reject
  -> ERP marks the FUNDING_INTENT notifications RESOLVED
```

## Changes by repo

### Core: `xbanka-web-app-backend`

| File | Change |
|---|---|
| `apps/wallet-service/src/erp-notifier.ts` (new) | Builds the payload and POSTs it to the ERP with the shared key. Returns a boolean, never throws, never logs the key. If `ERP_BASE_URL` or `INTERNAL_API_KEY` is unset it warns once and skips. |
| `apps/wallet-service/src/erp-notifier.spec.ts` (new) | 10 tests: payload shape, URL and header, failure logging without leaking the key, missing config. |
| `apps/wallet-service/src/wallet-service.service.ts` | `recordBankTransferIntent` now loads the customer's profile, and after saving calls `void notifyErpIntentDeclared(...)`. |
| `docs/flows/manual-funding-walkthrough/README.md` | Short note and env table for the new call. |

Payload sent to the ERP: `transactionId`, `reference`, `amount`, `customerName`, `customerXbId`,
`declaredAt`, `registeredFundingAccounts[]` (bank name, number, account name only).

### ERP backend: `Xbanka-backend`

| File | Change |
|---|---|
| `app/core/enums.py` | New `NotificationReferenceTypeEnum.FUNDING_INTENT`. `reference_id` is the core transaction id. |
| `alembic/versions/a9d3e5c7b1f2_add_funding_intent_reference_type.py` (new) | `ALTER TYPE ... ADD VALUE IF NOT EXISTS 'FUNDING_INTENT'`. Down revision `c3d34377f0d5`, the single head. Downgrade is a no-op. |
| `app/api/v1/routes/internal.py` (new), `routes/__init__.py` | `POST /api/internal/funding-intents/declared` (202). Notifies holders, queues emails, returns `{notified, duplicate}`. No holders is a 202 with `notified: 0`. |
| `app/utils/auth.py` | `require_internal_key`: constant-time check of `x-internal-key` against `INTERNAL_KEY`. Returns 403 if missing, wrong, or no key is configured. |
| `app/schemas/funding_intent.py` (new) | Request and response models with validation (amount > 0, length limits). |
| `app/services/erp_user.py` | `get_users_with_any_permission` (union, deduped) and `has_notification_for_reference` (idempotency). |
| `app/core/email_templates.py`, `app/core/email.py` | New email, subject `Transfer to confirm: ₦5,000.00`. Customer text is HTML-escaped. The button links to `{ERP_FRONTEND_URL}/finance?tab=funding`. |
| `app/api/v1/routes/transaction.py` | After a successful complete or reject, resolves the alert. A failure there is logged and never surfaces. |
| `tests/test_funding_intent_notification.py` (new) | 20 tests: permission union, overrides, Super Admin, key checks, notify and email, idempotent retry, validation, escaping, resolve. |

The in-app message reads: `"{customer} says they sent ₦X. Check the bank account."`, capped at 200 characters
(the column limit).

### ERP frontend: `xbankaAdmin`

| File | Change |
|---|---|
| `src/components/notifications-panel/notifications.ts` | Adds `FUNDING_INTENT` to the reference types. |
| `src/components/notifications-panel/notifications-panel.tsx` | New "Funding" filter tab and icon. Shows the declared amount and a Review button, with no payout affiliate or method rows. Clicking marks it read, opens the Funding Requests tab and closes the dropdown. A resolved one shows the badge and no button. |
| `src/app/(dashboard)/finance/page.tsx` | Reads `?tab=` (`payouts`, `funding`, `accounts`), including when already on the page. Wrapped in `Suspense`, which `useSearchParams` requires. |
| `notifications-panel.test.tsx`, `finance/page.test.tsx` (new) | 5 funding cases plus 4 page cases. |

Without this change a funding notification would have fallen into the payout branch and opened the payout
sidebar with a transaction id.

## Configuration

| Where | Variable | Value |
|---|---|---|
| Core | `ERP_BASE_URL` (**new**) | The ERP backend API origin, no path. Without it nothing is sent and the core logs one warning. |
| Core | `INTERNAL_API_KEY` (existing) | Must equal the ERP's `INTERNAL_KEY` in the same environment pair. |
| ERP backend | `INTERNAL_KEY` (existing) | Same value as above. The new endpoint refuses everything if it is empty. |
| ERP backend | `ERP_FRONTEND_URL` (existing) | Must be the real ERP frontend origin, because the email button is built from it. |
| ERP backend | `RESEND_API_KEY`, `TEST_EMAIL` (existing) | Sends the email. `TEST_EMAIL` is also copied on every email. |
| ERP frontend | none | The link is relative. |

All core services load `env_file: .env`, and the sender is `wallet-service`. After editing `.env`, recreate
the container (`docker compose up -d`) so it re-reads the file. Use a different key for each environment
pair, and make sure the core can reach the ERP backend over the network.

## Rollout order

1. **ERP backend:** run `alembic upgrade head`, then deploy. Confirm `INTERNAL_KEY` is set.
2. **ERP frontend:** deploy. This must go out before or with the core change, otherwise staff see a Review
   button that doesn't lead anywhere useful.
3. **Core:** set `ERP_BASE_URL`, confirm the key matches, recreate the containers, deploy.

## Tests

- ERP backend: the new file passes (20). The full suite was at 369 passed before the last email-link test
  was added.
- Core: 419 pass in `wallet-service`, plus the new notifier spec (10). One suite fails and is unrelated:
  `wallet-service.controller.spec.ts`, the NestJS scaffold test, can't resolve `DatabaseService`. It was
  failing before this change. `tsc` is clean.
- ERP frontend: 525 tests pass across 34 files. `tsc` and eslint are clean.
- **Not tested:** nothing has been run end to end across the services. Everything above used mocked HTTP and
  email.

## Known limits

- **Permission mismatch (accepted).** The audience is the three funding permissions, but the Funding
  Requests tab requires `finance:view_payments`, and its Confirm and Reject buttons require
  `finance:adjust_balance`. Someone holding only `approve_payments` or `reject_payments` would be notified
  but could land on "You don't have permission to view funding requests." We decided to leave this. It only
  matters if a role grants those permissions without `view_payments`, which we haven't checked.
- **The link opens the Pending list, not the specific intent.** The intent may not be on page 1, so
  highlighting it needs an extra lookup.
- **Completing or rejecting outside the ERP leaves the alert active.** Calling the core's internal
  endpoints directly doesn't involve the ERP. Staff are expected to use the ERP.
- **Preferences are ignored on purpose.** Honouring per-user email preferences would be a separate change.
