The MonoStack repository at `/app` is an npm workspace monorepo with four packages: `packages/core`, `packages/api`, `packages/ui`, and `packages/cli`. It currently has no `overrides` field in the root `/app/package.json`.

The platform team has written a migration RFC at `/app/docs/dependency-migration-rfc.md` that documents which transitive dependency versions must be pinned across the workspace to resolve peer conflicts, address known CVEs, and standardize tooling. The RFC is a living document — it went through several rounds of revision, so some sections were superseded, some proposals were rejected, and the final decisions are scattered across the document.

Your job is to implement the final override decisions from the RFC. Update the `overrides` field in `/app/package.json` to reflect exactly what the RFC ultimately settled on. Do not add overrides that were proposed but later rejected or superseded.

After updating `package.json`, run `npm install` from `/app` to apply the changes and verify the workspace installs cleanly.
