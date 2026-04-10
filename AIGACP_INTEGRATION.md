# AIGACP Module Integration Specification — Fix Module

**Status: Authoritative.** This document governs how Fix integrates into the AIGACP platform. Deviations require explicit approval and must be documented here.

---

## 1. MODULE INTEGRATION MODEL

### Mounting

Fix mounts as a route group inside the AIGACP Next.js application.

```
AIGACP App Router structure:
app/
  layout.tsx                  ← platform root layout (AuthProvider, design system)
  (platform)/                 ← shared platform chrome
    layout.tsx                ← PlatformLayout (nav, sidebar, header)
    dashboard/page.tsx
  (modules)/
    fix/                      ← Fix module root
      layout.tsx              ← Fix-specific layout shell (uses PlatformLayout)
      page.tsx                ← Fix home → chat/diagnostic interface
      session/[id]/page.tsx
      admin/page.tsx
      fleet/page.tsx
```

**Rules:**
- Fix has no standalone Next.js entry point in production.
- Fix's root URL is `/fix` within the AIGACP domain — not a separate domain.
- Fix registers itself in the platform's module registry. The registry drives navigation and entitlements.
- Module registry entry:

```typescript
// platform/modules/registry.ts
export const MODULE_REGISTRY: Module[] = [
  {
    id: "fix",
    label: "Fix — Diagnostics",
    href: "/fix",
    icon: "wrench",
    requiredRole: "fix:user",   // platform-level entitlement
  },
  // other modules...
];
```

### Shared Layout System

AIGACP provides `<PlatformLayout>` — the single layout wrapper for all modules.

```
<PlatformLayout>        ← platform: nav, sidebar, auth header, toast
  <FixLayoutShell>      ← Fix-specific chrome (diagnostic nav, session state)
    {children}
  </FixLayoutShell>
</PlatformLayout>
```

**Fix provides:** `<FixLayoutShell>` — scoped to diagnostic session context (current vehicle type, session status bar).

**Fix does not provide:** global nav, auth header, notification system, breadcrumbs. Those come from `<PlatformLayout>`.

**Removed from Fix's standalone frontend:**
- `app/layout.tsx` (root layout with AuthProvider) — replaced by platform root
- `middleware.ts` (route protection) — replaced by platform middleware
- Standalone login/register pages — replaced by platform auth pages

---

## 2. AUTHENTICATION

### Single Auth System: Supabase

AIGACP owns authentication. Fix has no auth system of its own.

**Platform-side (AIGACP):**
- Supabase Auth handles registration, login, logout, token refresh, session management.
- Platform's `AuthProvider` (at the root layout) exposes `useAuth()` to all modules.
- Platform middleware enforces authentication on all routes under `/(modules)/`.

**Fix frontend:**
- Fix calls `useAuth()` from the platform — never from its own context.
- Fix never calls auth endpoints directly.
- Fix reads: `user.id`, `user.email`, `session.access_token` (Supabase JWT).

**Fix backend:**
- Validates Supabase JWTs using the shared Supabase JWT secret.
- Does not issue its own JWTs.
- Does not set cookies.
- All protected endpoints use `get_current_user()` dependency, which now decodes a Supabase Bearer token from the `Authorization` header.

```python
# backend/app/core/deps.py (after migration)
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    db: AsyncSession = Depends(get_db),
) -> User:
    token = credentials.credentials
    payload = verify_supabase_jwt(token)          # validates against Supabase JWT secret
    supabase_user_id = payload["sub"]
    user = await get_or_create_fix_profile(db, supabase_user_id)  # Fix profile record
    return user
```

**Removed from Fix backend:**
- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `POST /api/auth/refresh`
- `GET /api/auth/me`
- Cookie-based token issuance
- `security.py` JWT creation functions (validation remains, rewritten for Supabase)

**Fix's User model becomes a profile extension:**

```sql
-- Fix profile — linked to Supabase user, not a standalone auth record
CREATE TABLE fix.user_profiles (
    supabase_user_id  UUID PRIMARY KEY,   -- Supabase auth.users.id
    is_admin          BOOLEAN DEFAULT FALSE,
    is_operator       BOOLEAN DEFAULT FALSE,
    created_at        TIMESTAMPTZ DEFAULT NOW()
);
```

Fix does not maintain password hashes. Identity lives in Supabase.

---

## 3. DATA SHARING

### What Is Shared Across Modules

| Data | Owner | Access Pattern |
|---|---|---|
| User identity (`user_id`, `email`) | Supabase / AIGACP | JWT claims — all modules read |
| Platform roles & entitlements | AIGACP | Platform auth context |
| Notification events | AIGACP event bus | Modules publish, platform delivers |
| Billing / subscription state | AIGACP | Platform context hook |
| Platform analytics events | AIGACP | Modules emit standardized events |

### What Remains Isolated in Fix

| Data | Rationale |
|---|---|
| Diagnostic sessions, messages, hypotheses, evidence | Core diagnostic state — Fix-owned |
| Tree engine state, scoring, exit decisions | Deterministic engine — Fix-owned |
| OBD/DTC lookups and results | Fix domain |
| Fleet records, operator assignments | Fix domain |
| Learning system weights and patterns | Fix domain |
| Telematics data | Fix domain |
| Uploaded images / media | Fix domain (stored under `fix/uploads/`) |

### Cross-Module Data Access Rules

1. **Other modules must not query Fix's database tables directly.** No cross-schema foreign keys into `fix.*`.
2. **Fix exposes summaries only** via platform event bus or a documented read-only API:
   - Event: `fix.session.completed` → `{ user_id, session_id, outcome, vehicle_type }` (no PHI, no evidence detail)
   - Event: `fix.safety.alert` → `{ user_id, severity, alert_type }` (for platform-level safety notification)
3. **Fix consumes** user identity only through Supabase JWT claims — never by calling another module's API.

---

## 4. API INTEGRATION

### Fix Backend: Dedicated Microservice

Fix keeps its FastAPI backend as an isolated service. It is not merged into a shared backend.

**Service topology:**

```
Browser
  → AIGACP Frontend (Next.js, all modules bundled)
      → AIGACP API Gateway
          → /fix/api/*  → Fix FastAPI service  (port 8001 internally)
          → /other/*    → Other module services
          → /auth/*     → Supabase Auth
      → Supabase (auth + shared user table)
      → PostgreSQL (Fix schema: fix.*)
```

**URL structure:**
- External: `https://aigacp.com/fix/api/sessions`
- Internal (Next.js rewrite): `/fix/api/*` → `http://fix-backend:8001/api/*`
- Fix's FastAPI base URL prefix remains `/api/` — the `/fix/` prefix is added by the gateway/rewrite only.

**Fix API client (frontend):**

```typescript
// frontend/src/lib/api.ts (after migration)
import { getSupabaseToken } from "@aigacp/platform/auth";

async function fixFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const token = await getSupabaseToken();   // platform utility — never custom auth
  const res = await fetch(`/fix/api${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...options?.headers,
    },
  });
  if (!res.ok) throw new ApiError(res.status, await res.text());
  return res.json();
}
```

**No cookie-based auth in the integrated app.** Supabase JWT is sent as a Bearer token.

**Fix backend CORS:**
- Allowed origins: AIGACP gateway origin only (not `localhost:3000` in production).
- Development: `localhost:3000` permitted for local dev only.

**Fix does not call other module backends.** If cross-module data is needed, it goes through the AIGACP event bus or a shared read API owned by AIGACP — not direct service-to-service calls.

---

## 5. UI CONSISTENCY

### Mandatory: AIGACP Design System

Fix uses the AIGACP design system exclusively. No parallel styling system exists.

**Token mapping (Fix standalone → AIGACP platform):**

| Fix standalone token | AIGACP platform token |
|---|---|
| `cyan-500`, `cyan-600` | `var(--color-primary)` |
| `slate-900`, `slate-800` | `var(--color-surface-strong)` |
| `shadow-card` | `var(--shadow-card)` |
| `shadow-card-hover` | `var(--shadow-card-hover)` |
| Plus Jakarta Sans | `var(--font-sans)` (platform font) |

**Shared component usage (mandatory):**

| Component | Source |
|---|---|
| Button, IconButton | `@aigacp/ui/Button` |
| Input, Textarea, Select | `@aigacp/ui/Form` |
| Card, CardHeader, CardBody | `@aigacp/ui/Card` |
| Modal, Dialog | `@aigacp/ui/Modal` |
| Toast, Alert | `@aigacp/ui/Feedback` |
| Badge, Pill | `@aigacp/ui/Badge` |
| Table, DataGrid | `@aigacp/ui/Table` |
| LoadingSpinner, Skeleton | `@aigacp/ui/Loading` |

**Fix-specific components permitted:**
- `<ChatInterface>` — diagnostic chat flow (no platform equivalent)
- `<MessageBubble>` — message rendering
- `<DiagnosticResult>` — result display
- `<HeavyEquipmentForm>` — vehicle context form
- `<HypothesisBar>` — live hypothesis confidence display
- `<SafetyAlert>` — safety interruption UI

Fix-specific components must still use platform tokens internally — no hardcoded colors, shadows, or fonts.

**Prohibited:**
- Separate `tailwind.config.ts` in Fix (use platform config)
- `globals.css` with custom CSS variables not defined in the platform design system
- Inline `style={{ color: "#06b6d4" }}` overrides that bypass tokens
- Any component from a third-party UI library not approved by the platform design system

---

## 6. DEPLOYMENT

### Fix Is Not Deployed Separately

Fix is part of the AIGACP platform deployment. There is no standalone Fix deployment in any environment beyond local development.

**Production service manifest (Docker Compose / Kubernetes):**

```yaml
# aigacp/docker-compose.yml (production-equivalent)
services:
  frontend:
    build: ./frontend          # All modules bundled — Fix code included
    ports: ["3000:3000"]

  api-gateway:
    image: aigacp-gateway
    routes:
      /fix/api/*: http://fix-backend:8001
      /other/api/*: http://other-backend:8002

  fix-backend:
    build: ./modules/fix/backend
    ports: ["8001:8001"]       # Internal only — not exposed externally
    environment:
      DATABASE_URL: postgresql://fix_user@db:5432/aigacp?options=-csearch_path=fix
      SUPABASE_JWT_SECRET: ${SUPABASE_JWT_SECRET}
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}

  db:
    image: postgres:16
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./db/migrations:/docker-entrypoint-initdb.d
```

**Rules:**
- Fix backend is never exposed on a public port — all traffic goes through the gateway.
- Fix frontend code lives in the AIGACP frontend build — not in a separate container.
- Fix does not have its own CI/CD pipeline. It is tested and deployed as part of the AIGACP pipeline.
- Fix's standalone `docker-compose.yml` is removed after migration. It may be retained under `docker-compose.dev.yml` for local-only development of the Fix module in isolation, with a clearly documented disclaimer.

**CI/CD gates (all must pass before AIGACP deploys):**
- Fix backend tests: all 698 tests pass (694 pass, 4 skip, 0 fail)
- Fix frontend: TypeScript compilation clean, no design system violations flagged by lint
- Integration test: Supabase JWT accepted by Fix backend end-to-end
- Integration test: Diagnostic session create/message/complete flow

---

## 7. MIGRATION PLAN

Migrate Fix from standalone app to integrated AIGACP module in six sequential phases. Each phase has a validation gate that must pass before the next phase begins.

### Phase M1 — Auth Cutover

**Goal:** Replace Fix's custom JWT auth with Supabase JWT validation.

Steps:
1. Add `SUPABASE_JWT_SECRET` to Fix backend environment.
2. Write `verify_supabase_jwt(token: str) -> dict` in `backend/app/core/security.py`.
3. Rewrite `get_current_user()` in `backend/app/core/deps.py` to validate Supabase Bearer token from `Authorization` header.
4. Create `fix.user_profiles` table (migration): `supabase_user_id UUID PK`, `is_admin BOOL`, `is_operator BOOL`.
5. Write `get_or_create_fix_profile(db, supabase_user_id)` to replace user lookup by internal ID.
6. Remove `backend/app/api/auth.py` and its router registration from `main.py`.
7. Remove cookie set/clear logic from all endpoints.
8. Update Fix frontend `lib/api.ts`: send `Authorization: Bearer <supabase_token>` using `getSupabaseToken()` from platform; remove `fetchWithAuth` refresh logic (Supabase SDK handles refresh).
9. Remove Fix's `AuthContext.tsx`, `lib/auth.ts`.
10. Remove Fix's `middleware.ts` (platform middleware takes over).

**Validation gate:**
- All 698 Fix backend tests pass with updated auth dependencies.
- `POST /api/sessions` with valid Supabase JWT returns 200.
- `POST /api/sessions` with no token returns 401.
- `POST /api/sessions` with Fix's old internal JWT returns 401.
- `GET /api/admin/...` with Supabase JWT + `is_admin=True` profile returns 200.

---

### Phase M2 — Routing Integration

**Goal:** Move Fix's Next.js pages into AIGACP app router.

Steps:
1. Create `app/(modules)/fix/` route group in AIGACP frontend.
2. Move Fix page components into this group:
   - `page.tsx` → `(modules)/fix/page.tsx`
   - `session/[id]/page.tsx`
   - `admin/page.tsx`
   - `fleet/page.tsx`
3. Move Fix components into `modules/fix/components/`.
4. Move Fix's `lib/api.ts`, `lib/admin.ts`, `lib/fleet.ts` into `modules/fix/lib/`.
5. Move Fix's `types/index.ts` into `modules/fix/types/`.
6. Remove Fix's root `app/layout.tsx`; add `(modules)/fix/layout.tsx` that wraps with `<PlatformLayout>` and `<FixLayoutShell>`.
7. Register Fix in `platform/modules/registry.ts`.
8. Update AIGACP platform middleware to include Fix routes in protected path list.
9. Update AIGACP `next.config.js`: add rewrite `/fix/api/*` → `http://fix-backend:8001/api/*`.

**Validation gate:**
- Fix pages load at `/fix`, `/fix/session/[id]`, `/fix/admin`, `/fix/fleet`.
- Platform nav renders Fix link.
- Unauthenticated user visiting `/fix` is redirected to platform login (not Fix login).
- No Fix-owned login or register page exists or is reachable.

---

### Phase M3 — API Gateway

**Goal:** Route all Fix API traffic through the AIGACP gateway.

Steps:
1. Update Fix backend `CORS_ORIGINS` to allow only the AIGACP gateway origin (not direct browser access).
2. Configure AIGACP gateway routing: `/fix/api/*` → Fix FastAPI service.
3. Update Fix frontend API client base URL: `/fix/api/*` (not `/api/*`).
4. Remove Fix's `next.config.js` API rewrite for direct backend access.
5. Verify rate limits are enforced at the gateway level (not duplicated in Fix backend; Fix backend rate limits can be removed or kept as defense-in-depth with higher ceilings).

**Validation gate:**
- Direct requests to `http://fix-backend:8001/api/*` from browser return CORS error.
- Requests through gateway at `/fix/api/*` succeed with valid Supabase JWT.
- Rate limiting at gateway enforces auth rate limits.

---

### Phase M4 — Design System

**Goal:** Replace Fix's standalone styling with AIGACP design system tokens and shared components.

Steps:
1. Audit all Fix components against platform component library. Produce a gap list.
2. Replace Fix's `tailwind.config.ts` imports with platform config extension.
3. Replace custom color tokens (`cyan-500`, `slate-900`) with platform tokens (`--color-primary`, `--color-surface-strong`).
4. Replace custom shadow utilities with platform shadow tokens.
5. Replace Fix UI primitives (buttons, inputs, cards) with `@aigacp/ui/*` equivalents.
6. Retain Fix-specific components (`ChatInterface`, `MessageBubble`, `DiagnosticResult`, `HeavyEquipmentForm`, `HypothesisBar`, `SafetyAlert`) — rewired to use platform tokens internally.
7. Remove Fix's `globals.css` custom variables.
8. Add lint rule: no hardcoded hex colors or non-token shadow values in `modules/fix/**`.

**Validation gate:**
- Design system audit lint passes with 0 violations.
- Visual regression test (screenshot diff) against approved Fix UI baseline.
- No Fix-specific `tailwind.config.ts` exists.
- Fix UI renders correctly in both light and dark modes if platform supports them.

---

### Phase M5 — Database

**Goal:** Move Fix's tables into the AIGACP shared PostgreSQL cluster under the `fix` schema.

Steps:
1. Create `fix` schema in AIGACP PostgreSQL: `CREATE SCHEMA fix;`.
2. Prefix all Fix migrations with `fix.` schema (e.g., `fix.sessions`, `fix.user_profiles`).
3. Update Fix backend `DATABASE_URL` to use shared cluster with `search_path=fix`.
4. Update all Fix SQLAlchemy models to use `schema="fix"` in `__table_args__`.
5. Run Fix migrations against AIGACP cluster in a staging environment.
6. Verify no cross-schema references exist between `fix.*` and other module schemas.
7. Migrate existing Fix production data (if any) into AIGACP cluster `fix` schema.

**Validation gate:**
- All 698 Fix tests pass against `fix` schema in AIGACP cluster.
- No SQLAlchemy model references to `public.*` schema remain.
- `psql \dt fix.*` lists all expected Fix tables.
- Other module tests still pass — no cross-schema leakage.

---

### Phase M6 — Deployment Cutover

**Goal:** Remove Fix as a standalone deployable unit; ship it as part of AIGACP.

Steps:
1. Add Fix backend service to AIGACP `docker-compose.yml` (and Kubernetes manifests if applicable).
2. Remove Fix's standalone `docker-compose.yml` from the Fix repo root (archive as `docker-compose.local-only.yml` with warning header if local dev isolation is needed).
3. Remove Fix's standalone frontend `Dockerfile` (frontend is now built as part of AIGACP frontend).
4. Add Fix backend to AIGACP CI/CD pipeline: build, test, push image, deploy.
5. Add Fix's 698 tests to AIGACP test suite run (backend) and Fix's frontend type-check to AIGACP frontend CI step.
6. Verify no Fix-specific deployment scripts, cron jobs, or runbooks reference a standalone Fix deployment.
7. Update operational runbooks: Fix is operated as part of AIGACP, not independently.

**Validation gate:**
- AIGACP CI/CD pipeline includes Fix backend tests and they pass.
- AIGACP deploys to staging; Fix is reachable at `https://staging.aigacp.com/fix`.
- No standalone Fix deployment exists or is deployable without AIGACP infrastructure.
- On-call runbooks updated.

---

## Enforcement

The following are hard rules, not guidelines. Any PR that violates them is rejected:

| Rule | Enforcement Point |
|---|---|
| Fix does not import from any other module's internal paths | Import lint rule in CI |
| Fix does not call Supabase auth APIs directly — only `getSupabaseToken()` from platform | Code review |
| Fix does not define its own auth endpoints | API contract test: `GET /fix/api/auth/*` returns 404 |
| Fix does not set cookies | Backend response header test in CI |
| Fix does not use hardcoded color values outside design tokens | Lint rule |
| Fix backend is not reachable directly from browser in production | CORS/gateway integration test |
| Fix is not deployable in isolation in production | No standalone Dockerfile or CI pipeline for Fix |
| All new LLM functions require explicit approval per CLAUDE.md | Architecture review gate |
| Orchestration-first checklist must be documented in PRs that change trees | PR template |
