# LNZ-ARCH-P0

Initial inventory, not a completed portability audit.

- Pure decision state: `helpers/lnz-research-state.tsx` (no imports).
- Persistence adapter: `helpers/db.tsx`, Kysely/Postgres, FLOOT_DATABASE_URL.
- AI adapter: `helpers/lnz-core-live-provider.tsx`, @floot/ai.
- Transport/auth: `helpers/flootAppExports.tsx`, @floot/apps.
- Worker: Python/Lean, GitHub Actions transport; separate from Floot runtime.

P1: extract pure decision state and test outside Floot. P2: provider, persistence and transport contracts; REST/MCP adapters. P3: portable worker. P4: independent end-to-end run. P5: security, scale, costs.

No changes to main or benchmark worker branch. No claims of industrial readiness. Benchmark execution remains disabled until preregistered gates pass.
