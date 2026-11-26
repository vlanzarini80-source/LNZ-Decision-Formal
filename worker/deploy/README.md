# Dedicated worker deployment candidate

Status: configuration only, not deployed or production approved.

Use a dedicated Linux VM, never a shared host with sensitive workloads.
Docker group membership is effectively root-equivalent. The gateway is trusted
host code; container isolation is not a guarantee against kernel exploits.

Prerequisites:
- Dedicated VM with Docker, Python 3, systemd and Caddy.
- Reviewed checkout installed read-only at /opt/lnz.
- Dedicated lnz-worker account and group.
- Verified Lean distribution at /opt/lean-dist and locally installed approved
  container image, with independently verified release hashes.
- Root-owned /etc/lnz/worker.env (mode 0600), containing LNZ_IMAGE_ID,
  LNZ_LEAN_DIST and a randomly generated LNZ_LEAN_WORKER_TOKEN.
- DNS hostname and HTTPS ingress; expose only HTTPS and required ACME ports,
  not port 8080. Set LNZ_WORKER_HOST in Caddy's service environment.

Before enabling public access:
1. Enforce authenticated request quotas and bounded admission queue at ingress.
2. Bound executor output during capture, not after capture.
3. Verify timeout cleanup, restart recovery, and concurrent overload behavior.
4. Pin and independently verify toolchain and image digests.
5. Add durable request receipts and replay/idempotency handling.
6. Run authenticated positive and negative probes over HTTPS from Floot.
7. Keep arbitrary Lean source disabled.

The service uses a single execution slot. Proxy connection limits are not a
bounded admission queue. Do not expose this candidate publicly until the
above controls are tested. No cloud resources are provisioned by these files.
