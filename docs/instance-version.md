# Instance version

Every Integray instance exposes an **unauthenticated** GET:

```
{baseUrl}/api/Integray
```

No Remote control token. No `{CompanySlug}`. This is **not** Remote API (`/api/Remote/...`).

Example: `https://test-prod.integray.app/api/Integray`

## Response

```json
{
  "IssuedTo": null,
  "Expiration": null,
  "Version": "rel-2025-03.017 2026-09-24 11:20:33\n",
  "RenewalNotSuccessfull": false,
  "LicenseIsNotValid": false
}
```

The field that matters for development is **`Version`**. Split it on the first space:

| Part | Example | Meaning |
|------|---------|---------|
| **First token** | `rel-2025-03.017` | Product line / git branch we develop against (`rel-YYYY-MM.patch`) |
| **Remainder** | `2026-09-24 11:20:33` | Date and time of this build (UTC-style stamp from the build; trailing newline is normal) |

License fields (`IssuedTo`, `Expiration`, `RenewalNotSuccessfull`, `LicenseIsNotValid`) are not used for versioning.

## Features from a given version

Some platform behaviour exists **only from a given first token**. When recording or using such a fact, name that token (e.g. “from `rel-2025-03.017`”). Do not treat a later **build timestamp** as a new product version.

Before assuming an instance has that behaviour, run:

```bash
python scripts/get-instance-version.py \
  --connection projects/<name>/.integray-connection.json
```

or `--base-url {baseUrl}`. Stdout:

```
productLine=rel-2025-03.017
buildStamp=2026-09-24 11:20:33
```

`productLine` is the first token of `Version`. Do not curl `/api/Integray` by hand when this script is available. Token is not sent.
