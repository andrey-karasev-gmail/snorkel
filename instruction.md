The MonoStack repository at `/app` is an npm workspace monorepo with four packages: `packages/core`, `packages/api`, `packages/ui`, and `packages/cli`. It currently has no `overrides` field in the root `/app/package.json`.

The platform team has written a migration RFC at `/app/docs/dependency-migration-rfc.md` that documents which transitive dependency versions must be pinned across the workspace to resolve peer conflicts, address known CVEs, and standardize tooling. The RFC is a living document — it went through several rounds of revision, so some sections were superseded, some proposals were rejected, and the final decisions are collected in the **Final Decisions** section near the end of the document.

Your job is to implement the final override decisions from the RFC. Update the `overrides` field in `/app/package.json` to reflect exactly what the RFC ultimately settled on. Do not add overrides that were proposed but later rejected or superseded. Only the five packages whose overrides were approved should appear in the overrides block.

After updating `package.json`, regenerate the lock file and install from `/app`:

```sh
cd /app
rm -f package-lock.json
npm install --prefer-offline
```

Deleting the existing `package-lock.json` is required — the current lock file pins the old package versions, and npm will not change them unless it rebuilds the lock file from scratch. Use `--prefer-offline` because this environment has restricted outbound registry access; all required package versions are already cached locally.