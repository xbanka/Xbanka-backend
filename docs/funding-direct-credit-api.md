# Crediting a wallet without a funding intent

For the ERP **credit directly** flow. A customer sent money to Xbanka's account but never tapped "I have sent the money", so there is no pending funding intent to complete. Staff find the transfer on the bank statement, look up which customer registered the sending account, and credit that customer's NGN wallet.

Two endpoints do the work, with two optional helpers around them:

| Step | Endpoint | Permission |
|---|---|---|
| Check no intent exists (helper) | `GET /api/transactions/funding/intents?accountNumber=` | `VIEW_PAYMENTS` |
| 1. Find the customer | `GET /api/transactions/funding/lookup` | `ADJUST_BALANCE` |
| Upload proof, optional (helper) | `POST /api/transactions/funding/attachments` | `ADJUST_BALANCE` |
| 2. Credit the wallet | `POST /api/transactions/funding/credit` | `ADJUST_BALANCE` |

All requests need `Authorization: Bearer <token>`. No token → `401`; missing permission → `403`. Hide the flow from staff who lack `ADJUST_BALANCE`.

> These routes are pass-throughs to the core backend. Success bodies are the core backend's responses, and its error status codes and messages come back unchanged (`detail` holds the core backend's response text).

---

## The flow

1. **Check for a pending intent.** `GET /api/transactions/funding/intents?accountNumber=<sender account>`. If a PENDING intent exists, stop and use the complete-intent screen instead (see [funding-intents-api.md](funding-intents-api.md)). Crediting directly would credit the wallet correctly but leave the customer with a PENDING row next to the COMPLETED one. If the list is empty, continue.
2. **Look up the customer** (endpoint 1 below). Handle zero, one or several matches.
3. **Confirm the match.** Show `accountName`, `customer.name`, `xbId`, `email` and `bank`, and have staff check them against the sender on the bank statement.
   - Block when `customer.isActive` is `false`: a suspended account cannot be credited.
   - If `wallet` is `null` the customer has no NGN wallet yet. Warn or block.
4. **Enter the credit details** from the bank statement: amount, bank reference, and optionally proof files (upload each first, see [Upload proof](#upload-proof-optional)).
5. **Review and confirm.** This credits real money, so show a summary (customer, amount, reference, proof) and require an explicit confirm. Disable the button while the request runs.
6. **Credit the wallet** (endpoint 2 below). Show the new balance and transaction ID.

---

## 1. Look up the customer — `GET /api/transactions/funding/lookup`

Finds the customer who registered the sending account in the app.

```http
GET /api/transactions/funding/lookup?accountNumber=7054178290&bankCode=100004
```

| Param | Required | Notes |
|---|---|---|
| `accountNumber` | Yes | Exactly 10 digits: the account the money was sent **from** |
| `bankCode` | No | Narrows to one bank. Use it when the same number exists at several banks |

### Response — `200`

An **array**, because the same number can be registered at different banks.

```json
[
  {
    "fundingAccountId": "7c0c1d2e-5b4a-4c53-9d57-0f3f0f4a1b11",
    "bank": "Paycom (Opay)",
    "accountName": "OMOLADE OLUWASEGUN AKANBI",
    "customer": {
      "userId": "991fbf45-8c5a-4840-9f4f-8af81c586922",
      "xbId": "XB123",
      "email": "customer@example.com",
      "isActive": true,
      "name": "Omolade Akanbi"
    },
    "wallet": { "currency": "NGN" }
  }
]
```

| Result | What to do |
|---|---|
| `[]` | Nobody registered that account. Tell staff the customer must add it in the app first, and stop |
| One item | Show it for confirmation |
| Several items | Let staff pick by `bank` and `accountName`, or search again with `bankCode` |

Keep the chosen item's `fundingAccountId`. It goes into the credit request.

---

## Upload proof (optional)

```http
POST /api/transactions/funding/attachments
Content-Type: multipart/form-data   (field: file)
```

JPEG, PNG, WebP or PDF, up to 5 MB (the content is checked, not just the extension). Returns `{ "url": "..." }`. Collect up to **5** URLs and pass them as `attachmentUrls` when crediting.

---

## 2. Credit the wallet — `POST /api/transactions/funding/credit`

```http
POST /api/transactions/funding/credit
```

```json
{
  "fundingAccountId": "7c0c1d2e-5b4a-4c53-9d57-0f3f0f4a1b11",
  "amount": 2000,
  "reference": "100004261006204500123456",
  "creditedBy": "admin@example.com",
  "attachmentUrls": []
}
```

| Field | Required | Notes |
|---|---|---|
| `fundingAccountId` | Yes | From the lookup match |
| `amount` | Yes | NGN. Minimum `0.01`, at most 2 decimals |
| `reference` | Yes | The bank's transaction reference or session ID, 4 to 100 characters. The core backend trims and uppercases it |
| `creditedBy` | Yes | **The signed-in admin's email**, stored for audit. See the note below |
| `attachmentUrls` | No | Up to 5 URLs from the upload step |

The transaction is stored with reference `BANKFUND-<reference>`.

### Response — `200`

```json
{
  "duplicate": false,
  "transactionId": "<uuid>",
  "reference": "BANKFUND-100004261006204500123456",
  "amount": 2000,
  "balance": 12000,
  "creditedAt": "2026-11-12T10:15:30.000Z"
}
```

The customer sees a COMPLETED deposit and gets an in-app notification.

### The bank reference is the idempotency key

One bank reference can be credited **once**, across all intents and direct credits. That makes retrying safe:

- **Timeout or network error:** retry the same request. You will not double-credit.
- **`duplicate: true`:** the same reference with the same details was already credited. Show "Already credited" with the returned result. It is not an error.
- **`409`:** the reference was already used with a different amount or account. Ask staff to re-check the reference. Do not retry.

> **`creditedBy` is not verified by the server.** It is stored as sent, so the frontend must send the logged-in admin's own email. A wrong value corrupts the audit trail.

---

## Validate in the UI first

The amount, reference and attachment limits are enforced by the core backend, and its error text comes back unchanged. Validate before sending so staff get clear messages:

- `amount` ≥ 0.01 with at most 2 decimals.
- `reference` 4 to 100 characters.
- At most 5 attachments, each JPEG, PNG, WebP or PDF and under 5 MB.
- `accountNumber` is exactly 10 digits (the lookup returns `422` otherwise).

## Errors

| Status | Where | When |
|---|---|---|
| 401 | Both | Missing or invalid token |
| 403 | Both | Missing `ADJUST_BALANCE`, or the customer account is suspended (credit) |
| 400 | Credit | Validation failed (bad amount, short reference, bad attachment URLs) |
| 404 | Credit | Funding account not found. Redo the lookup |
| 409 | Credit | Reference already used with different details |
| 422 | Lookup | `accountNumber` missing or not 10 digits, or `bankCode` empty |
| 502 | Both | The core backend could not be reached. Retrying is safe |

Other statuses are the core backend's, passed through.

## Which call to use

| Situation | Call |
|---|---|
| Money arrived and the customer declared it (pending intent) | Complete the intent. Not this flow |
| Customer declared it but no money arrived | Reject the intent. Not this flow |
| Money arrived, customer never declared it | **This flow:** lookup, then credit |
| Not sure whether an intent exists | `GET /api/transactions/funding/intents?accountNumber=` first |
