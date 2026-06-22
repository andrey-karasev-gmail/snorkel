# RFC-2024-047: MonoStack Dependency Security Migration

**Status:** FINAL — Implementation Required  
**Authors:** Platform Team (J. Hartwell, S. Okonkwo, T. Bergström)  
**Created:** 2024-01-08  
**Last Updated:** 2024-03-22  
**Reviewers:** Security Guild, Frontend Guild, DevOps  

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Background and Motivation](#2-background-and-motivation)
3. [Scope](#3-scope)
4. [Initial Proposals (January 2024)](#4-initial-proposals-january-2024)
5. [Security Audit Findings](#5-security-audit-findings)
6. [Revised Proposals — Round 2 (February 2024)](#6-revised-proposals--round-2-february-2024)
7. [Peer Compatibility Analysis](#7-peer-compatibility-analysis)
8. [Rejected Proposals and Rationale](#8-rejected-proposals-and-rationale)
9. [Frontend Guild Review](#9-frontend-guild-review)
10. [DevOps Review](#10-devops-review)
11. [Round 3 Revisions (March 2024)](#11-round-3-revisions-march-2024)
12. [Final Decisions](#12-final-decisions)
13. [Implementation Notes](#13-implementation-notes)
14. [Appendix A: CVE Reference Table](#14-appendix-a-cve-reference-table)
15. [Appendix B: Superseded Proposals Log](#15-appendix-b-superseded-proposals-log)
16. [Appendix C: Peer Dependency Conflict Matrix](#16-appendix-c-peer-dependency-conflict-matrix)

---

## 1. Executive Summary

MonoStack has accumulated a set of transitive dependency vulnerabilities identified during our Q1 2024 security audit. This RFC documents the proposed resolution strategy, the deliberation process across three rounds of review, and the final authoritative override decisions to be applied to the workspace root `package.json`.

The overrides mechanism in npm workspaces allows us to enforce specific versions of transitive dependencies across all packages without requiring each package to independently pin them. This is the recommended approach for monorepos managing shared transitive exposure.

**This RFC went through three rounds of revision.** Earlier sections contain proposals that were subsequently superseded or rejected. The canonical final decisions are recorded in [Section 12](#12-final-decisions). Implementors should read Section 12 as the authoritative source and treat earlier version proposals as historical context only.

---

## 2. Background and Motivation

### 2.1 The Problem with Transitive Dependencies

MonoStack's four packages — `@monostack/core`, `@monostack/api`, `@monostack/ui`, and `@monostack/cli` — each declare their own direct dependencies. However, those direct dependencies pull in transitive dependencies at versions that have known CVEs or peer compatibility issues.

The standard approach of asking each package owner to upgrade their own deps has proven slow and inconsistent. The Platform Team received security advisory notices for five separate transitive packages between November 2023 and January 2024. Three attempts to coordinate cross-package upgrades during that period failed to reach full rollout before the next advisory arrived.

### 2.2 Why npm Overrides

npm workspaces introduced the `overrides` field in the root `package.json` to solve exactly this class of problem. When an override is specified, npm enforces that version across the entire dependency tree, regardless of what individual packages or their transitive dependencies request.

```json
{
  "overrides": {
    "some-package": "1.2.3"
  }
}
```

This approach:
- Requires only a single change in the root `package.json`
- Takes effect for all packages in the workspace on the next `npm install`
- Is explicit and reviewable in version control
- Does not require upstream packages to release new versions

### 2.3 Scope of This RFC

This RFC specifically covers the `overrides` block in `/app/package.json`. It does not cover:
- Direct dependency versions in individual package `package.json` files
- Dev dependency upgrades
- Node.js runtime version changes
- Any changes to CI configuration

### 2.4 Prior Art

In Q3 2022 we addressed a similar issue with `minimist` and `node-fetch` using manual `npm dedupe` passes. That approach worked for two packages but scaled poorly. This RFC establishes `overrides` as the standard going forward.

---

## 3. Scope

### 3.1 Packages in Scope

All four MonoStack workspace packages are in scope:

| Package | Path | Primary Language |
|---|---|---|
| `@monostack/core` | `packages/core` | JavaScript |
| `@monostack/api` | `packages/api` | JavaScript |
| `@monostack/ui` | `packages/ui` | JavaScript |
| `@monostack/cli` | `packages/cli` | JavaScript |

### 3.2 Dependencies Under Review

The following transitive dependencies were flagged for override consideration:

1. **lodash** — prototype pollution vulnerability
2. **semver** — regular expression denial of service (ReDoS)
3. **axios** — server-side request forgery (SSRF)
4. **express** — path traversal vulnerability
5. **react** — version fragmentation across packages causing double-render issues

### 3.3 Out of Scope

The following were considered but explicitly excluded:

- `webpack` — no CVE, upgrade would be a breaking change requiring extensive testing
- `babel` — frontend team requested deferral to Q3 2024
- `eslint` — dev dependency only, no production risk

---

## 4. Initial Proposals (January 2024)

> **NOTE:** This section contains the original Round 1 proposals from January 2024.
> Several of these were revised in subsequent rounds. Do not use these version numbers
> as the final implementation target. See Section 12 for final decisions.

### 4.1 lodash

**Background:** CVE-2021-23337 affects lodash versions prior to 4.17.21. The vulnerability allows prototype pollution via the `zipObjectDeep` function. Our `@monostack/core` package depends on `lodash@4.17.20`, which is one patch version behind the fix.

**Initial Proposal (Round 1):**
```
lodash: "4.17.21"
```

Rationale: The fix is a single patch version bump. No breaking changes. The vulnerability has a CVSS score of 7.2 (High). Immediate patching is recommended.

**Round 1 Status:** Accepted as proposed. No objections raised during initial review.

### 4.2 semver

**Background:** CVE-2022-25883 affects semver versions prior to 7.5.2. The vulnerability is a ReDoS (Regular Expression Denial of Service) in the `semver` package's version parsing logic. An attacker providing a crafted version string could cause unbounded CPU usage.

**Initial Proposal (Round 1):**
```
semver: "7.5.4"
```

Rationale: `7.5.4` was the latest stable release at the time of the initial proposal and includes the ReDoS fix. Semver follows strict semver itself so a minor version bump within the 7.x range is expected to be backward compatible.

**Round 1 Status:** Provisionally accepted, pending security team review of whether 7.5.4 is sufficient or if a higher minor version is required.

### 4.3 axios

**Background:** CVE-2023-45857 affects axios versions prior to 1.6.0. The vulnerability is a server-side request forgery (SSRF) issue related to improper handling of `XSRF-TOKEN` cookies that could expose credentials to unintended third-party origins.

**Initial Proposal (Round 1):**
```
axios: "1.4.0"
```

Rationale: The Platform Team initially proposed `1.4.0` as a conservative intermediate upgrade that would address most known issues while limiting the blast radius of the upgrade.

**Round 1 Status:** DISPUTED. Security team noted that `1.4.0` does NOT fix CVE-2023-45857. The fix was introduced in `1.6.0`. The Round 1 proposal was flagged as insufficient.

### 4.4 express

**Background:** CVE-2024-29041 affects express versions prior to 4.19.2. The vulnerability involves improper input sanitization in URL parsing, which can lead to path traversal under specific proxy configurations.

**Initial Proposal (Round 1):**
```
express: "4.18.3"
```

Rationale: `4.18.3` was an intermediate patch release the team was already planning to adopt.

**Round 1 Status:** REJECTED by Security team. CVE-2024-29041 is not fixed until `4.19.2`. See Section 8.1 for full rejection rationale.

### 4.5 react

**Background:** No CVE. The issue is version fragmentation: `@monostack/ui` uses `react@18.2.0` while newer packages added after the initial setup have been picking up `react@18.0.0` and `react@18.1.0` from their own transitive chains. This causes the "multiple React instances" problem where hooks throw invariant violations at runtime.

**Initial Proposal (Round 1):**
```
react: "18.2.0"
```

Rationale: Pin everything to the version already in `@monostack/ui`.

**Round 1 Status:** Accepted in principle. Frontend Guild requested review of whether a newer minor version should be targeted instead.

---

## 5. Security Audit Findings

The Security Guild conducted a full audit of the MonoStack dependency tree on 2024-01-29. The following findings were incorporated into the Round 2 revision process.

### 5.1 lodash — Confirmed

The audit confirmed the lodash finding from Section 4.1. `4.17.21` fully resolves CVE-2021-23337.

> *"The fix is minimal and well-understood. No compatibility risk. We recommend immediate adoption."*
> — Security Guild Audit Report, p. 4

### 5.2 semver — Escalated

The audit found that `7.5.4`, the Round 1 proposal, did not represent the latest stable release by January 2024. The security team noted:

> *"While 7.5.4 addresses the original ReDoS CVE, subsequent releases through 7.6.x have included additional hardening of the regex parser and improved handling of edge-case version strings. We recommend targeting the latest stable 7.6.x release rather than stopping at 7.5.4."*
> — Security Guild Audit Report, p. 7

The audit did not specify an exact 7.6.x version, leaving the selection to the Platform Team.

### 5.3 axios — Confirmed Insufficient

The audit confirmed the Security team's objection to the Round 1 proposal:

> *"CVE-2023-45857 is categorized CVSS 6.5 (Medium). The vulnerability was introduced in axios 0.21.1 and fully remediated in 1.6.0. Any override below 1.6.0 will leave MonoStack exposed. The `1.4.0` proposal in the current RFC draft does not meet our patching SLA for CVSS ≥ 5.0 vulnerabilities."*
> — Security Guild Audit Report, p. 9

### 5.4 express — Confirmed Insufficient

The audit confirmed the rejection of `4.18.3`:

> *"CVE-2024-29041 is a path traversal vulnerability introduced by improper handling of the Host header. It was fixed in 4.19.2. Intermediate versions 4.18.x and 4.19.0 / 4.19.1 are all vulnerable. The only acceptable target is 4.19.2 or higher."*
> — Security Guild Audit Report, p. 11

### 5.5 react — No CVE, Recommendation Revised

The audit did not flag a CVE for react. However, the Frontend Guild raised an additional concern during the audit review period:

> *"React 18.3.0 introduced a deprecation warning for legacy rendering patterns that several components in `@monostack/ui` use. We are already tracking the migration to the new API. Given that we need to override react anyway, we recommend targeting 18.3.1 (the first stable release after 18.3.0 that resolved a regression in the new warnings) to get ahead of the deprecation timeline."*
> — Frontend Guild comment on audit draft, 2024-02-05

---

## 6. Revised Proposals — Round 2 (February 2024)

> **NOTE:** This section documents Round 2 proposals from February 2024.
> Some of these were further revised in Round 3. See Section 12 for final decisions.

Based on the Security Audit findings, the Platform Team revised all five proposals:

### 6.1 lodash — Round 2

No change from Round 1. `4.17.21` confirmed as the target.

```
lodash: "4.17.21"
```

**Round 2 Status:** Confirmed.

### 6.2 semver — Round 2

The Security Guild's recommendation was to target the latest 7.6.x. At the time of Round 2 (February 2024), `7.6.0` was the latest release in the 7.6.x series.

```
semver: "7.6.0"
```

**Round 2 Status:** Provisionally accepted. The Platform Team noted this should be re-evaluated before final implementation in case a newer patch had been released.

### 6.3 axios — Round 2

Revised upward from the rejected `1.4.0` to address CVE-2023-45857:

```
axios: "1.6.0"
```

**Round 2 Status:** Accepted by Security team as meeting the minimum bar. DevOps requested a check for breaking changes between `1.3.4` (the current version in `@monostack/api`) and `1.6.0`.

### 6.4 express — Round 2

Revised from rejected `4.18.3`:

```
express: "4.19.2"
```

**Round 2 Status:** Accepted. This is the minimum version that resolves CVE-2024-29041. No further objections.

### 6.5 react — Round 2

Revised per Frontend Guild recommendation to include deprecation migration:

```
react: "18.3.1"
```

**Round 2 Status:** Accepted by Frontend Guild. DevOps noted this requires verifying that `react-dom` is also updated to match, but since we are using `overrides` the `react-dom` package will be handled separately only if fragmentation is detected there too.

---

## 7. Peer Compatibility Analysis

This section records the peer dependency compatibility checks performed before finalizing the Round 2 proposals.

### 7.1 lodash 4.17.21

Lodash does not declare peer dependencies. Compatible with all existing packages. No issues found.

### 7.2 semver 7.6.x

`semver` is widely used as an internal utility. The 7.x API is stable and backward compatible with 7.0.x. The change from `7.5.3` (current in `@monostack/core`) to `7.6.x` is non-breaking.

One transitive consumer — `@npmcli/package-json` — was found to peer-require `semver@^7.0.0`, which is satisfied by any 7.x version.

### 7.3 axios 1.6.x

The DevOps team's breaking change analysis found:

- **axios interceptors:** No breaking changes in the interceptor API between 1.3.x and 1.6.x.
- **CancelToken:** The `CancelToken` API was deprecated in 1.5.0 but not removed. Still functional in 1.6.x.
- **TypeScript types:** Improved in 1.6.x. No regressions.
- **`withCredentials` default:** No change.
- **SSRF patch:** The patch changes how `XSRF-TOKEN` is sent but only in cross-origin scenarios. MonoStack's API package uses axios for server-to-server calls only and does not use XSRF tokens.

**Conclusion:** The upgrade from `1.3.4` to `1.6.0` has no breaking impact on MonoStack's usage patterns.

### 7.4 express 4.19.2

Express follows semver. The `4.18.x` to `4.19.x` bump is a minor version increment indicating new features and potential deprecated API warnings, but no breaking changes.

The path traversal fix in `4.19.2` involves changes to the `res.redirect()` and router URL normalization logic. No MonoStack code paths use the affected patterns.

### 7.5 react 18.3.1

`react-dom` must match the `react` version. Both are included in the `@monostack/ui` dependencies at `18.2.0`. After applying the override:

- `react` will be forced to `18.3.1` workspace-wide
- `react-dom@18.2.0` in `@monostack/ui` will remain at `18.2.0` unless separately overridden

The Frontend Guild confirmed that `react@18.3.1` is compatible with `react-dom@18.2.0` for their current usage patterns, but noted this is a temporary state and a follow-up ticket has been filed to update `react-dom` in `@monostack/ui/package.json` directly.

---

## 8. Rejected Proposals and Rationale

### 8.1 express 4.18.3 — REJECTED

**Proposal:** `express: "4.18.3"`  
**Proposed by:** Platform Team (Round 1)  
**Rejected by:** Security Guild  
**Reason:** CVE-2024-29041 was introduced in express versions prior to `4.19.2`. Versions `4.18.3`, `4.19.0`, and `4.19.1` are all affected. The patch was first included in `4.19.2`. Any override below `4.19.2` leaves the vulnerability unaddressed.

### 8.2 axios 1.4.0 — REJECTED

**Proposal:** `axios: "1.4.0"`  
**Proposed by:** Platform Team (Round 1, conservative approach)  
**Rejected by:** Security Guild  
**Reason:** CVE-2023-45857 is not present in versions prior to `0.21.1` and was fixed in `1.6.0`. Version `1.4.0` is within the vulnerable range. The proposal was described in the audit as "insufficient to address the stated security concern."

### 8.3 semver 7.5.4 — SUPERSEDED (not rejected)

**Proposal:** `semver: "7.5.4"`  
**Proposed by:** Platform Team (Round 1)  
**Status:** Superseded by Round 2 proposal  
**Reason:** Not rejected for correctness — `7.5.4` does fix the original ReDoS CVE. However, the Security Guild recommended targeting the latest 7.6.x for additional hardening. The Round 2 proposal of `7.6.0` superseded this.

### 8.4 webpack and babel — OUT OF SCOPE

Both packages were raised in early discussions but explicitly removed from scope. See Section 3.3.

### 8.5 react 18.2.0 — SUPERSEDED (not rejected)

**Proposal:** `react: "18.2.0"`  
**Proposed by:** Platform Team (Round 1)  
**Status:** Superseded by Round 2 proposal  
**Reason:** Frontend Guild recommended `18.3.1` to align with deprecation migration timeline. The `18.2.0` proposal was not incorrect but was superseded by the revised recommendation.

---

## 9. Frontend Guild Review

The Frontend Guild reviewed the react-related decisions on 2024-02-12. Key discussion points:

### 9.1 react 18.3.x Deprecation Warnings

React 18.3.0 adds `console.error` deprecation warnings for:
- `ReactDOM.render()` (deprecated since React 18.0 but warning-free until 18.3)
- `ReactDOM.hydrate()` (same)
- `React.createFactory()` (removed in 19.0)
- String refs

`@monostack/ui` uses `ReactDOM.render()` in its test harness. The Frontend Guild's recommendation to adopt `18.3.1` was partly motivated by wanting visibility into these deprecation warnings before React 19 makes them breaking.

### 9.2 Why 18.3.1 Not 18.3.0

React 18.3.0 was released on 2024-04-22 and `18.3.1` was released on 2024-05-01 to fix a regression in the new deprecation warning output that caused crashes in certain SSR environments. MonoStack does not use SSR currently, but the guild recommended `18.3.1` as the safe choice.

### 9.3 Guild Decision

> *"The Frontend Guild approves the override of react to 18.3.1. We do not recommend 18.3.0 due to the regression. We do not recommend anything below 18.3.0 as it would undermine the deprecation visibility goal."*
> — Frontend Guild Review Notes, 2024-02-12

---

## 10. DevOps Review

The DevOps team reviewed the full proposal set on 2024-02-19. Their review focused on build pipeline impact and npm install reproducibility.

### 10.1 package-lock.json Considerations

The DevOps team noted that adding `overrides` will cause npm to restructure parts of `node_modules` on the next `npm install`. This will produce a diff in `package-lock.json`. The team flagged this as expected and not a concern, but asked that the PR that implements the overrides include a full regeneration of `package-lock.json` rather than an incremental update.

### 10.2 CI Build Time

The full `npm install` with overrides is expected to add approximately 15-30 seconds to CI build times due to the deduplication pass. This is acceptable.

### 10.3 Docker Layer Cache Invalidation

Any change to `package.json` will invalidate the Docker layer cache for the `npm install` step. The DevOps team requested the implementing engineer note this in the PR description so that the first pipeline run after the change is not mistaken for a build failure.

### 10.4 DevOps Approval

> *"DevOps approves the proposal with the notes above. No objections to the specific version selections."*
> — DevOps Review Sign-off, 2024-02-19

---

## 11. Round 3 Revisions (March 2024)

> **NOTE:** This section documents the final round of revisions from March 2024.
> The semver version was updated based on a newer release becoming available.
> All other packages were confirmed as-is from Round 2.

Between the Round 2 proposal (February) and the implementation deadline (March 22), the Security Guild requested a final check on semver to confirm whether a newer patch had been released.

### 11.1 semver — Final Check

The Platform Team checked the semver release history on 2024-03-15:

| Version | Release Date | Notable Changes |
|---|---|---|
| 7.6.0 | 2024-01-12 | Additional ReDoS hardening |
| 7.6.1 | 2024-02-08 | Fix regression in range comparator |
| 7.6.2 | 2024-03-01 | Fix edge case in `satisfies()` with pre-release tags |
| 7.6.3 | 2024-03-14 | Security: additional input length limit enforcement |

**Round 3 Decision:** Update semver target from `7.6.0` (Round 2) to `7.6.3` (latest at time of implementation). The Security Guild specifically endorsed `7.6.3` for the input length enforcement change.

> *"7.6.3 adds explicit input length limits that further reduce ReDoS attack surface. We recommend this over 7.6.0."*
> — Security Guild, Round 3 sign-off, 2024-03-15

```
semver: "7.6.3"
```

### 11.2 axios — Final Check

The Platform Team checked whether a newer patch was available. At the time of the Round 3 review, `axios` releases in the 1.6.x series included:

| Version | Release Date | Notable Changes |
|---|---|---|
| 1.6.0 | 2023-10-26 | CVE-2023-45857 fix |
| 1.6.1 | 2023-11-08 | Fix regression in response interceptors |
| 1.6.2 | 2023-11-21 | Fix FormData handling edge case |
| 1.6.3 | 2023-12-26 | Fix null-byte injection in URL params |
| 1.6.4 | 2024-01-25 | Dependency updates |
| 1.6.5 | 2024-02-20 | Fix for chunked transfer encoding |
| 1.6.6 | 2024-02-26 | Security: Patch for prototype pollution in mergeDeep |
| 1.6.7 | 2024-03-11 | Fix regression introduced in 1.6.6 |
| 1.6.8 | 2024-03-15 | Patch for SSRF in redirect handling |

The Security Guild reviewed the 1.6.x changelog and noted:

> *"1.6.6 addressed a prototype pollution issue and 1.6.8 patched an SSRF regression in redirect handling. We recommend targeting 1.6.8 as the final anchor for this RFC cycle. The Round 2 proposal of 1.6.0 remains functionally correct for the original CVE-2023-45857, but 1.6.8 is a strictly better target given subsequent patches."*
> — Security Guild, Round 3 sign-off, 2024-03-15

**Round 3 Decision:** Update axios target from `1.6.0` (Round 2) to `1.6.8`.

```
axios: "1.6.8"
```

### 11.3 All Other Packages — Confirmed

lodash, express, and react were confirmed as unchanged from their Round 2 versions:

- `lodash: "4.17.21"` — no change
- `express: "4.19.2"` — no change
- `react: "18.3.1"` — no change

---

## 12. Final Decisions

> **This section is the single authoritative source for implementation.**
> All earlier sections are historical record. Only the versions listed here
> should be applied to the workspace root `package.json` overrides block.

After three rounds of review by the Platform Team, Security Guild, Frontend Guild, and DevOps, the following overrides are approved for implementation:

### 12.1 Approved Overrides

```json
{
  "overrides": {
    "lodash": "4.17.21",
    "semver": "7.6.3",
    "axios": "1.6.8",
    "express": "4.19.2",
    "react": "18.3.1"
  }
}
```

### 12.2 Summary of Final Version Selections

| Package | Current Version | Override Target | Primary Reason | CVE / Issue |
|---|---|---|---|---|
| lodash | 4.17.20 | **4.17.21** | Prototype pollution fix | CVE-2021-23337 |
| semver | 7.5.3 | **7.6.3** | ReDoS hardening + input limits | CVE-2022-25883 |
| axios | 1.3.4 | **1.6.8** | SSRF fix + subsequent patches | CVE-2023-45857 |
| express | 4.18.2 | **4.19.2** | Path traversal fix | CVE-2024-29041 |
| react | 18.2.0 | **18.3.1** | Version standardization + deprecation visibility | N/A |

### 12.3 What Was NOT Included

The following were explicitly excluded from the overrides block:

- `react-dom` — managed directly in `@monostack/ui/package.json`; separate follow-up ticket filed
- `webpack` — deferred to Q3 2024
- `babel` — deferred to Q3 2024

### 12.4 Implementation Steps

1. Update `/app/package.json` to add the `overrides` block as specified in 12.1
2. Run `npm install` from `/app` to apply the overrides and regenerate `package-lock.json`
3. Verify clean install (no peer dependency warnings related to the overridden packages)
4. Submit PR with the updated `package.json` and regenerated `package-lock.json`

---

## 13. Implementation Notes

### 13.1 Order of Operations

The overrides block should be added to the root `package.json` **before** running `npm install`. Adding it after install will not take effect until install is re-run.

### 13.2 Expected Warnings

After applying the overrides, `npm install` may emit warnings along the lines of:

```
npm warn overriding lodash@4.17.20 with lodash@4.17.21
```

These warnings are expected and confirm the override mechanism is working. They are not errors.

### 13.3 CI Implications

The first CI run after this change will trigger a full Docker rebuild due to layer cache invalidation (see Section 10.3). This is expected. The build time will be longer than normal for that one run.

### 13.4 Rollback

If an issue is discovered after applying the overrides, the rollback procedure is:
1. Remove the `overrides` block from `package.json`
2. Run `npm install`
3. Revert the `package-lock.json` to the pre-override version

---

## 14. Appendix A: CVE Reference Table

| CVE | Package | CVSS Score | Affected Versions | Fixed In |
|---|---|---|---|---|
| CVE-2021-23337 | lodash | 7.2 (High) | < 4.17.21 | 4.17.21 |
| CVE-2022-25883 | semver | 5.3 (Medium) | 7.x < 7.5.2 | 7.5.2+ |
| CVE-2023-45857 | axios | 6.5 (Medium) | 0.21.1 – 1.5.x | 1.6.0+ |
| CVE-2024-29041 | express | 6.1 (Medium) | < 4.19.2 | 4.19.2 |

---

## 15. Appendix B: Superseded Proposals Log

| Section | Package | Superseded Version | Replaced By | Round |
|---|---|---|---|---|
| 4.3 | axios | 1.4.0 | 1.6.0 (Round 2) → 1.6.8 (Round 3) | 2, 3 |
| 4.4 | express | 4.18.3 | 4.19.2 | 2 |
| 4.2 | semver | 7.5.4 | 7.6.0 (Round 2) → 7.6.3 (Round 3) | 2, 3 |
| 4.5 | react | 18.2.0 | 18.3.1 | 2 |
| 6.2 | semver | 7.6.0 | 7.6.3 | 3 |
| 6.3 | axios | 1.6.0 | 1.6.8 | 3 |

---

## 16. Appendix C: Peer Dependency Conflict Matrix

This matrix documents peer dependency relationships between the overridden packages and the rest of the MonoStack dependency tree.

| Override | Peer Consumers in Tree | Peer Requirement | Satisfied by Override |
|---|---|---|---|
| lodash@4.17.21 | 14 packages | `^4.0.0` or `^4.17.0` | Yes |
| semver@7.6.3 | 8 packages | `^7.0.0` | Yes |
| axios@1.6.8 | 1 package (api) | `^1.0.0` | Yes |
| express@4.19.2 | 1 package (api) | `^4.0.0` | Yes |
| react@18.3.1 | 3 packages (ui, react-dom, testing-library) | `^18.0.0` | Yes |

All overrides satisfy the peer requirements of their consumers. No peer conflicts are introduced by these overrides.

---

---

## 17. Appendix D: Full CVE Technical Analysis

This appendix provides deep technical breakdowns of each CVE addressed by this RFC, including exploit mechanics, affected code paths, and remediation verification methodology.

### D.1 CVE-2021-23337 — lodash Prototype Pollution via `zipObjectDeep`

**Severity:** High (CVSS 7.2)
**CWE:** CWE-1321 (Improperly Controlled Modification of Object Prototype Attributes)
**Affected Versions:** < 4.17.21
**Fixed In:** 4.17.21

#### D.1.1 Exploit Mechanics

The vulnerability exists in lodash's `zipObjectDeep` function. This function is designed to create an object from arrays of paths and values, supporting nested path notation. The flaw occurs when a crafted path string containing `__proto__` or `constructor.prototype` is passed as a key.

Example exploit payload:
```javascript
const _ = require('lodash');

// Exploiting zipObjectDeep
_.zipObjectDeep(['__proto__.polluted'], [true]);
console.log({}.polluted); // true — global prototype has been mutated
```

The same vulnerability class also affects related functions:
- `_.set()` with `__proto__` path
- `_.setWith()` with `__proto__` path
- `_.merge()` with `__proto__` key in source object

However, CVE-2021-23337 specifically calls out `zipObjectDeep` as the primary attack vector.

#### D.1.2 Impact in MonoStack Context

`@monostack/core` uses lodash `4.17.20` for several utility functions:
- `_.groupBy()` — used in report aggregation (not vulnerable)
- `_.merge()` — used in config merging (vulnerable call path exists)
- `_.get()` and `_.set()` — used extensively for nested config access

The `_.merge()` usage in config merging is the relevant risk surface. If any configuration data originates from user-controlled input (e.g., API request bodies, CLI flags), a crafted payload could pollute `Object.prototype`, causing unexpected behavior across the entire Node.js process.

In `@monostack/api`, the Express route handlers accept JSON bodies that are passed to `_.merge()` in the middleware stack. This creates a viable attack chain:
```
POST /api/config
Content-Type: application/json
{"__proto__": {"isAdmin": true}}
```
If this body is passed through `_.merge()` without sanitization, every subsequently created object would have `isAdmin: true`.

#### D.1.3 Remediation Verification

The fix in `4.17.21` adds path segment validation in the `baseSet` internal function. Specifically, it rejects any path segment that equals `__proto__`, `prototype`, or `constructor` when the parent is a plain object or function.

To verify the fix:
```javascript
const _ = require('lodash@4.17.21');
_.zipObjectDeep(['__proto__.polluted'], [true]);
console.log({}.polluted); // undefined — prototype was not mutated
```

Security team verification script (run as part of the audit):
```bash
node -e "
const _ = require('lodash');
const before = Object.keys(Object.prototype).length;
_.zipObjectDeep(['__proto__.test'], [1]);
const after = Object.keys(Object.prototype).length;
process.exit(after > before ? 1 : 0);
"
```
Exit code 0 confirms the fix is active. Verified against `4.17.21` on 2024-01-29.

#### D.1.4 Why `4.17.21` and Not a Higher Version

As of January 2024, `4.17.21` is the latest release of lodash `4.x`. There is no `4.17.22` or later. The lodash maintainers have not published a new release since December 2021, so `4.17.21` is definitively the latest and the fix target.

---

### D.2 CVE-2022-25883 — semver ReDoS in Version Parsing

**Severity:** Medium (CVSS 5.3)
**CWE:** CWE-1333 (Inefficient Regular Expression Complexity)
**Affected Versions:** 7.x < 7.5.2 (also affects older major versions with different fix points)
**Fixed In:** 7.5.2 (initial), further hardened in 7.6.x

#### D.2.1 Exploit Mechanics

The `semver` package's version parsing relies on regular expressions. Prior to `7.5.2`, the regex used for parsing version strings did not limit input length, allowing a crafted input of repeating characters to cause catastrophic backtracking.

Vulnerable regex pattern (simplified):
```
/^(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$/
```

For very long prerelease identifiers like `1.2.3-` followed by 50,000 characters, the regex engine backtracks exponentially, causing the parsing to hang for seconds or minutes.

Proof of concept:
```javascript
const semver = require('semver');
const malicious = '1.2.3-' + 'a'.repeat(50000) + '!';
console.time('parse');
semver.valid(malicious); // hangs for many seconds in affected versions
console.timeEnd('parse');
```

On a modern CPU, this input can cause `semver.valid()` to take over 30 seconds, effectively blocking the Node.js event loop for that duration.

#### D.2.2 Impact in MonoStack Context

`@monostack/core` uses `semver@7.5.3` internally for version comparison in its package manifest processing logic. The relevant code path:
```javascript
// packages/core/src/manifest.js
const semver = require('semver');
function isCompatible(version, range) {
  return semver.satisfies(version, range);
}
```

If `version` or `range` is ever derived from external input (e.g., a plugin manifest uploaded by an end user), a malicious input could block the event loop. The Security Guild classified this as Medium severity because:
1. The input must be of significant length (tens of thousands of characters) to trigger catastrophic backtracking
2. The attack surface requires the caller to pass unvalidated external strings to `semver`
3. There is no evidence of direct external input flowing to `semver` in current code

However, as a widely depended-upon utility, the risk of this being exploited through a transitive dependency's usage is non-trivial.

#### D.2.3 Fix Evolution: 7.5.2 → 7.5.4 → 7.6.0 → 7.6.3

The fix for CVE-2022-25883 was introduced in `7.5.2` with input length limits on version strings (max 256 characters). However, subsequent releases continued hardening:

| Version | Fix Applied |
|---|---|
| 7.5.2 | Initial fix: input length limit of 256 characters on version strings |
| 7.5.3 | Additional length checks on range strings and prerelease identifiers |
| 7.5.4 | Regex engine hints to prevent backtracking on valid but complex inputs |
| 7.6.0 | Parser rewritten to use non-backtracking patterns for core version components |
| 7.6.1 | Fix regression in range comparator introduced in 7.6.0 |
| 7.6.2 | Edge case fix in `satisfies()` with pre-release version comparisons |
| 7.6.3 | Explicit input length enforcement at function entry points (belt-and-suspenders) |

The Security Guild's recommendation to target `7.6.3` reflects the cumulative hardening. Even though `7.5.2` technically "fixes" the original CVE, each subsequent release adds defense-in-depth.

#### D.2.4 Backward Compatibility Assessment

All changes from `7.5.3` to `7.6.3` are backward compatible within the semver 7.x API. The only breaking behavior change is that inputs exceeding the length limits now return `null` (for `semver.valid()`) or throw a `TypeError` (for `semver.coerce()`) rather than hanging. This is the desired behavior for any code path that previously would have hung indefinitely.

MonoStack's usage of `semver.satisfies()` and `semver.valid()` is all within version strings of normal length (< 50 characters). No behavioral changes are expected.

---

### D.3 CVE-2023-45857 — axios SSRF via XSRF-TOKEN Exposure

**Severity:** Medium (CVSS 6.5)
**CWE:** CWE-918 (Server-Side Request Forgery)
**Affected Versions:** 0.21.1 – 1.5.x
**Fixed In:** 1.6.0

#### D.3.1 Exploit Mechanics

The vulnerability is in how axios handles the `XSRF-TOKEN` cookie in cross-origin requests. Axios was designed to automatically include the value of the `XSRF-TOKEN` cookie in the `X-XSRF-TOKEN` request header for CSRF protection. However, a bug introduced in `0.21.1` caused this header to be sent on cross-origin requests as well as same-origin requests.

When a browser-based application using axios makes a cross-origin request, the `X-XSRF-TOKEN` header (containing the user's CSRF token) is sent to the third-party origin. If the application is configured to use cookies for XSRF protection (common in frameworks like Laravel, Angular, Django REST), this effectively leaks the user's CSRF token to untrusted origins.

Attack scenario:
1. A vulnerable application at `app.example.com` uses axios with XSRF cookie protection
2. User visits `app.example.com` which sets `XSRF-TOKEN` cookie
3. Attacker tricks user into visiting `evil.com` which includes a page that loads an image from `api.example.com`
4. axios, running in the `evil.com` context, sends `X-XSRF-TOKEN` with the token value to `api.example.com`
5. If the API accepts this token from cross-origin, the attacker can forge authenticated requests

Note: This is primarily a client-side (browser) vulnerability. Server-side uses of axios are not directly affected.

#### D.3.2 Impact in MonoStack Context

`@monostack/api` uses axios for server-to-server HTTP calls only. The package runs in a Node.js server environment, not in a browser. The `XSRF-TOKEN` vulnerability is strictly a browser-environment concern because:
1. Node.js does not have the concept of same-origin policy
2. No browser cookie jar is involved in server-to-server calls
3. The `X-XSRF-TOKEN` header is never set in the server-side axios usage

**Why override anyway?** Two reasons:
1. The 1.6.x series includes additional security patches unrelated to CVE-2023-45857 (prototype pollution fix in 1.6.6, SSRF in redirect handling in 1.6.8)
2. Standardizing on a modern version reduces audit surface and ensures future browser-facing usage of axios (if added) starts from a secure baseline

#### D.3.3 The Round 1 Failure: Why `1.4.0` Was Wrong

The Platform Team's initial proposal of `1.4.0` was based on a misreading of the CVE description. The team believed `1.4.0` was released after the CVE was reported and therefore included the fix. This was incorrect.

The timeline:
- CVE-2023-45857 was publicly reported in November 2023
- axios `1.6.0` (which fixes it) was released in October 2023 — before the CVE was publicly disclosed
- The fix was already in `1.6.0` for a different, related security reason
- `1.4.0` was released in April 2023, before the fix was developed

The Security Guild's audit clarified that the CVE number assignment date (November 2023) does not correspond to the fix date. The fix was already present in `1.6.0` released in October 2023.

#### D.3.4 Version Selection: From 1.6.0 to 1.6.8

| Version | Security Relevance |
|---|---|
| 1.6.0 | CVE-2023-45857 fix (XSRF-TOKEN cross-origin exposure) |
| 1.6.6 | Prototype pollution in `mergeDeep` utility function |
| 1.6.8 | SSRF vulnerability in redirect handling (new CVE) |

The Security Guild recommended `1.6.8` in Round 3 because:
- `1.6.6` fixed a prototype pollution issue that could be exploited if axios options are derived from untrusted input
- `1.6.8` fixed a new SSRF issue in redirect handling where a crafted 3xx response could redirect to an internal network address
- Both are relevant to MonoStack's server-side usage of axios

---

### D.4 CVE-2024-29041 — express Path Traversal via Host Header

**Severity:** Medium (CVSS 6.1)
**CWE:** CWE-22 (Improper Limitation of a Pathname to a Restricted Directory)
**Affected Versions:** < 4.19.2
**Fixed In:** 4.19.2

#### D.4.1 Exploit Mechanics

The vulnerability is in Express's URL parsing and redirect handling when the application is deployed behind a proxy. Specifically, `res.redirect()` does not adequately sanitize the redirect target when it is derived from user-controlled input (including the `Host` header) under certain proxy configurations.

When Express is configured with `trust proxy` and the proxy forwards a `Host` header, a crafted `Host` header value can cause `res.redirect()` to generate a redirect to an unintended URL, including paths that traverse directory structures or protocol-relative URLs that redirect to attacker-controlled domains.

Simplified example:
```javascript
// Vulnerable Express route
app.set('trust proxy', true);
app.get('/login', (req, res) => {
  const returnTo = req.query.return || '/dashboard';
  res.redirect(returnTo); // safe
});

// The vulnerability is in Express's internal handling of Host headers
// in redirect URL generation, not directly in application code
```

The full exploit requires a specific proxy configuration and the application to use `res.redirect()` with dynamic paths. The details of the exact payload are not included in this RFC to avoid providing attack instructions.

#### D.4.2 Impact in MonoStack Context

`@monostack/api` uses Express `4.18.2` and is deployed behind an AWS Application Load Balancer (ALB) with `trust proxy` enabled. The API includes redirect endpoints for authentication flows (OAuth callback redirects).

The Security Guild assessed the risk as Medium because:
1. The `trust proxy` setting is enabled (necessary condition for the exploit)
2. Redirect endpoints exist in the authentication flow
3. The `Host` header from the ALB is forwarded to Express

The fix in `4.19.2` adds stricter URL normalization in the router and in `res.redirect()` that prevents the Host header from being used in ways that could cause unintended redirects.

#### D.4.3 Why the Intermediate Versions Don't Fix It

`4.18.3`, `4.19.0`, and `4.19.1` were all considered as potential targets:

- `4.18.3` — Does not include the CVE-2024-29041 fix. Released before the fix was developed.
- `4.19.0` — Released 2024-03-25. Includes the initial attempt at a fix, but the fix was incomplete. Express maintainers subsequently discovered a bypass.
- `4.19.1` — Released 2024-03-26. Attempted to close the bypass from `4.19.0`, but was still found to be incomplete.
- `4.19.2` — Released 2024-03-25 (yes, same day as `4.19.0`, different commit). This is the version that the Express security team has confirmed fully resolves the issue.

The confusing release timeline (4.19.0 and 4.19.2 on the same day) is documented in the Express security advisory. The team effectively published `4.19.0`, immediately found a bypass, and published `4.19.2` before any users could widely upgrade. `4.19.1` was an intermediate attempt that is also incomplete.

The Security Guild's guidance is explicit: only `4.19.2` or later is acceptable.

---

### D.5 react Version Fragmentation — Not a CVE

**Issue Type:** Runtime stability / functional correctness
**Affected Versions:** Multiple React 18.x versions coexisting in the same npm workspace
**Fixed By:** Overriding to a single version via npm overrides

#### D.5.1 The Multiple Instances Problem

React relies on module-level singletons for its hook state management. When two different packages in a monorepo depend on different versions of React, npm may install both versions (e.g., `react@18.0.0` in `node_modules` and `react@18.2.0` in `node_modules/.package-a/node_modules`). When both instances are loaded by the same JavaScript process, React's internal invariant checks trigger an error:

```
Error: Invalid hook call. Hooks can only be called inside the function body of a function component.
```

This error occurs even when hooks are called correctly — the issue is that the hook is registered in one React instance but the component is rendered by another.

#### D.5.2 Version Inventory in MonoStack

Before the override, the MonoStack workspace had the following React version situation:

| Package | Direct React Dep | Resolved Version |
|---|---|---|
| `@monostack/ui` | `react@^18.2.0` | 18.2.0 |
| `@monostack/ui` (transitive via `react-beautiful-dnd`) | `react@^16.8.3 \|\| ^17 \|\| ^18` | 18.0.0 |
| `@monostack/cli` | none | — |
| `@monostack/api` | none | — |
| `@monostack/core` (transitive via `react-query@3.x`) | `react@^16.8.0 \|\| ^17.0.0 \|\| ^18.0.0` | 18.1.0 |

The transitive React pulls created three different installed versions:
- `node_modules/react` → `18.2.0`
- `node_modules/react-beautiful-dnd/node_modules/react` → `18.0.0`
- `node_modules/react-query/node_modules/react` → `18.1.0`

This created the double-render and hook invariant violation symptoms reported in the Q4 2023 bug tracker (ticket MONO-8841: "Drag-and-drop causes React hook invariant violation in production").

#### D.5.3 The 18.3.1 Choice

The Frontend Guild initially wanted to just standardize on `18.2.0`, the version already in use by the primary `@monostack/ui` package. However, `18.3.1` was chosen for two additional reasons:
1. It introduces deprecation warnings for APIs that React 19 will remove, giving the team visibility into required migration work
2. `18.3.0` had an SSR regression that was fixed in `18.3.1`

The override forces all three previously conflicting instances to resolve to `18.3.1`.

---

## 18. Appendix E: Stakeholder Communication Log

This appendix excerpts key communications from the RFC review process. Full threads are archived in Confluence under `Platform Engineering > RFC Archive > RFC-2024-047`.

### E.1 Initial Slack Thread — #platform-eng (2024-01-08)

**J. Hartwell** [9:02 AM]: Hey team, we have a security advisory situation to work through. The Q1 audit flagged five transitive deps with CVEs or stability issues. I'm going to write up an RFC this week. Pinging @S. Okonkwo and @T. Bergström to co-author.

**S. Okonkwo** [9:15 AM]: On it. I'll take the semver and lodash sections since I've been tracking those CVEs since Q4. @T. Bergström can you own the express and axios analysis?

**T. Bergström** [9:22 AM]: Sure. I looked at the axios one last week — heads up, the initial thought of 1.4.0 is probably wrong, CVE-2023-45857 wasn't fixed until 1.6.0. I'll put the full analysis in the RFC.

**J. Hartwell** [9:31 AM]: Good catch on axios. Let's make sure we're citing the actual CVE fix versions, not just "latest at the time we noticed." Security Guild will check.

**Security Guild Rep (A. Patel)** [10:47 AM]: Just saw this thread. We want to be in the review loop. Can you add a formal review gate before finalizing? We need to verify each proposed version actually contains the fix, not just a version that post-dates the CVE report.

**J. Hartwell** [10:52 AM]: Absolutely. Added as a formal review step. You'll get the draft RFC for review before we post Round 2 proposals.

---

### E.2 Email Thread: Security Guild Formal Review Request (2024-01-24)

**From:** J. Hartwell  
**To:** security-guild@monostack.internal  
**Subject:** RFC-2024-047 — Security Review Request  
**Date:** 2024-01-24

> Hi Security Guild,
>
> Attached is the current draft of RFC-2024-047 covering five transitive dependency overrides for the MonoStack workspace. We have Round 1 proposals for all five packages. Per our discussion in #platform-eng, we'd like your team to:
>
> 1. Confirm each proposed version actually contains the CVE fix
> 2. Recommend if a higher version should be targeted
> 3. Flag any packages we may have missed
>
> We're on a timeline to implement by end of March 2024. Please return your feedback by February 2.
>
> Packages under review:
> - lodash (CVE-2021-23337): proposing 4.17.21
> - semver (CVE-2022-25883): proposing 7.5.4
> - axios (CVE-2023-45857): proposing 1.4.0
> - express (CVE-2024-29041): proposing 4.18.3
> - react (version fragmentation, no CVE): proposing 18.2.0
>
> Thanks,  
> J. Hartwell, Platform Team

---

**From:** A. Patel (Security Guild Lead)  
**To:** J. Hartwell; security-guild@monostack.internal  
**Subject:** RE: RFC-2024-047 — Security Review Request  
**Date:** 2024-01-29

> J.,
>
> We've completed our review. Full report attached (see also Appendix D of this RFC). Summary of our findings:
>
> **lodash 4.17.21 — CONFIRMED CORRECT.** This is the exact fix version. No issues.
>
> **semver 7.5.4 — CONDITIONALLY APPROVED.** Fixes the original CVE. However, the 7.6.x series has additional hardening we recommend. We'll note this for re-evaluation before final implementation.
>
> **axios 1.4.0 — REJECTED.** This does not fix CVE-2023-45857. The fix was introduced in 1.6.0. Please revise to at minimum 1.6.0. We recommend checking the 1.6.x changelog for any subsequent security patches.
>
> **express 4.18.3 — REJECTED.** This does not fix CVE-2024-29041. Only 4.19.2 contains the verified fix. Versions 4.19.0 and 4.19.1 have an incomplete fix. Use only 4.19.2.
>
> **react 18.2.0 — NO SECURITY OBJECTION.** This is a stability/compatibility concern, not a CVE. We defer to Frontend Guild on version selection. We note that 18.3.x introduces deprecation warnings that may be relevant.
>
> Full audit report attached. Please revise your Round 2 proposals based on our findings.
>
> Regards,  
> A. Patel, Security Guild Lead

---

### E.3 Slack Thread — #frontend-guild (2024-02-05)

**M. Chen (Frontend Guild Lead)** [2:15 PM]: @team — Platform is asking us to review the react override version for RFC-2024-047. They're considering 18.2.0. What's our take?

**D. Kowalczyk** [2:28 PM]: 18.2.0 is fine from a compatibility standpoint but why stop there? We're eventually going to need to deal with the 18.3.x deprecation warnings before React 19 drops. If we're touching this now, we should target 18.3.1.

**R. Nakamura** [2:35 PM]: Agreed on 18.3.1. One note: 18.3.0 has a regression in SSR scenarios. Not relevant to us right now (we don't do SSR) but 18.3.1 is cleaner.

**M. Chen** [2:41 PM]: OK team consensus: recommend 18.3.1 to Platform. We also want to confirm that react-dom should NOT be in the overrides — we'll handle the react-dom version directly in @monostack/ui since it's a direct dep there.

**J. Hartwell (Platform)** [3:02 PM]: Got it. 18.3.1 for react, react-dom stays out of overrides, @monostack/ui team handles react-dom upgrade directly. Will update the RFC.

---

### E.4 Email Thread: DevOps Review (2024-02-16)

**From:** T. Bergström  
**To:** devops@monostack.internal  
**Subject:** RFC-2024-047 — DevOps Review Request  
**Date:** 2024-02-16

> Hi DevOps,
>
> We're finalizing Round 2 proposals for our transitive dependency override RFC. Before we proceed to implementation, we need your team's sign-off on:
>
> 1. Build pipeline impact (especially Docker layer cache invalidation)
> 2. npm install reproducibility with the overrides block
> 3. Any CI concerns
>
> The full RFC is linked in Confluence. The proposed overrides are:
> - lodash: 4.17.21
> - semver: 7.6.0 (updated per security recommendation)
> - axios: 1.6.0 (corrected from rejected 1.4.0)
> - express: 4.19.2 (corrected from rejected 4.18.3)
> - react: 18.3.1 (updated per frontend guild recommendation)
>
> Please confirm no objections and flag any concerns by February 19.
>
> Thanks,  
> T. Bergström

---

**From:** F. O'Sullivan (DevOps Lead)  
**To:** T. Bergström; devops@monostack.internal  
**Subject:** RE: RFC-2024-047 — DevOps Review Request  
**Date:** 2024-02-19

> T.,
>
> DevOps review complete. Approving with the following notes:
>
> **Cache invalidation:** Any change to package.json (including adding an `overrides` block) will bust the Docker layer cache at the npm install step. The first pipeline run after this change will be slow. Please note this in your PR description so the ops team doesn't mistake it for a build failure.
>
> **Lock file:** The PR must include a regenerated package-lock.json. Partial regeneration is not acceptable — run a clean `npm install` (or `npm ci` followed by `npm install` to regenerate) and commit the full updated lockfile.
>
> **Build time:** We estimate 15-30 additional seconds per pipeline run due to the deduplication pass npm performs when overrides are active. This is within acceptable bounds.
>
> **Rollback:** Document the rollback procedure. If we need to emergency-revert, the procedure should be in the PR description.
>
> No other concerns. Approved.
>
> F. O'Sullivan, DevOps Lead

---

### E.5 Slack Thread — Round 3 Security Check (2024-03-15)

**J. Hartwell** [10:05 AM]: We're at the implementation deadline for RFC-2024-047. Before we go, Security Guild asked for a final check on semver and axios to confirm we have the latest in the 7.6.x and 1.6.x series. @A. Patel confirming versions?

**A. Patel** [10:23 AM]: Checked release history. For semver: latest in 7.6.x as of today is 7.6.3 (released 2024-03-14). Has additional input length enforcement. Recommend using 7.6.3 over our Round 2 proposal of 7.6.0.

**A. Patel** [10:24 AM]: For axios: latest in 1.6.x is 1.6.8 (released 2024-03-15, literally yesterday). It patches an SSRF in redirect handling. We recommend targeting 1.6.8 over our Round 2 proposal of 1.6.0.

**J. Hartwell** [10:31 AM]: Updating RFC now. So final overrides: lodash 4.17.21 (unchanged), semver 7.6.3 (bumped from 7.6.0), axios 1.6.8 (bumped from 1.6.0), express 4.19.2 (unchanged), react 18.3.1 (unchanged).

**T. Bergström** [10:35 AM]: Confirmed, updating implementation ticket.

**S. Okonkwo** [10:38 AM]: Adding the Round 3 changes to Appendix B superseded proposals log. RFC will be final as of today.

---

## 19. Appendix F: Package Version Release Timelines

This appendix provides complete release timelines for each overridden package, covering the period relevant to this RFC's deliberation (Q4 2023 through Q1 2024).

### F.1 lodash Release History (relevant period)

| Version | Release Date | Notable Changes | Security Relevant |
|---|---|---|---|
| 4.17.19 | 2020-07-10 | Remove `array.sort` usage | No |
| 4.17.20 | 2020-08-14 | Fix `_.toNumber` edge case | No |
| 4.17.21 | 2021-02-20 | Fix prototype pollution in `zipObjectDeep` (CVE-2021-23337) | **YES** |

**Note:** No lodash 4.x releases have occurred since February 2021. The `4.17.21` release remains the latest and final 4.x release. There is ongoing community discussion about lodash 5.x (ESM-native rewrite) but no stable release as of March 2024.

**Historical context:** The lodash team has announced that `4.x` is in maintenance mode. Bug fixes and security patches will continue to be applied, but no new features. The team recommends migrating to native ES features (`.flatMap()`, `Object.fromEntries()`, etc.) where lodash is used for simple utilities.

For MonoStack, this means:
- `4.17.21` is the correct target and will remain so for the foreseeable future
- No future lodash `4.x` version will supersede `4.17.21` unless a new security issue is discovered
- The team should plan a migration away from lodash for new code, but existing usage on `4.17.21` is acceptable

---

### F.2 semver Release History (relevant period)

| Version | Release Date | Notable Changes | Security Relevant |
|---|---|---|---|
| 7.5.1 | 2023-04-03 | Performance improvements | No |
| 7.5.2 | 2023-06-13 | Initial ReDoS fix (CVE-2022-25883) | **YES** |
| 7.5.3 | 2023-06-21 | Additional length checks on range strings | **YES** |
| 7.5.4 | 2023-07-17 | Regex engine hints for backtracking prevention | **YES** |
| 7.6.0 | 2024-01-12 | Non-backtracking regex patterns for core version components | **YES** |
| 7.6.1 | 2024-02-08 | Fix regression in range comparator from 7.6.0 | Yes (regression fix) |
| 7.6.2 | 2024-03-01 | Fix edge case in `satisfies()` with pre-release tags | No |
| 7.6.3 | 2024-03-14 | Input length enforcement at function entry points | **YES** |

**Important distinction:** `7.5.3` was the version installed in `@monostack/core` at the time of the RFC (not `7.5.2`). The difference matters for CVE assessment: `7.5.3` does fix CVE-2022-25883, but the 7.6.x series provides stronger protection.

**Round 1 proposal of `7.5.4`** would have been an improvement but not optimal.  
**Round 2 proposal of `7.6.0`** addressed the Security Guild's recommendation to use 7.6.x hardening.  
**Round 3 decision of `7.6.3`** captures all subsequent security-relevant fixes in the 7.6.x series.

---

### F.3 axios Release History (relevant period)

| Version | Release Date | Notable Changes | Security Relevant |
|---|---|---|---|
| 1.3.4 | 2023-02-13 | Fix FormData circular reference | No |
| 1.4.0 | 2023-04-27 | Node.js stream improvements | No |
| 1.5.0 | 2023-08-25 | Deprecate CancelToken API | No |
| 1.5.1 | 2023-09-12 | Fix regression in response transformation | No |
| 1.6.0 | 2023-10-26 | **Fix CVE-2023-45857 (XSRF-TOKEN cross-origin exposure)** | **YES** |
| 1.6.1 | 2023-11-08 | Fix regression in response interceptors from 1.6.0 | Yes (regression fix) |
| 1.6.2 | 2023-11-21 | Fix FormData handling edge case | No |
| 1.6.3 | 2023-12-26 | Fix null-byte injection in URL params | **YES** |
| 1.6.4 | 2024-01-25 | Dependency updates (follow-me-ip removed) | No |
| 1.6.5 | 2024-02-20 | Fix for chunked transfer encoding on slow connections | No |
| 1.6.6 | 2024-02-26 | **Fix prototype pollution in `mergeDeep`** | **YES** |
| 1.6.7 | 2024-03-11 | Fix regression introduced in 1.6.6 (mergeDeep) | Yes (regression fix) |
| 1.6.8 | 2024-03-15 | **Fix SSRF vulnerability in redirect handling** | **YES** |

**Key observation:** Between Round 2 (proposing `1.6.0`) and Round 3 (finalizing `1.6.8`), three additional security-relevant fixes were released: `1.6.3` (null-byte injection), `1.6.6` (prototype pollution), and `1.6.8` (SSRF in redirects). This retroactively validates the Security Guild's process of doing a final check before implementation.

**Why `1.4.0` was the wrong answer (reprise):** `1.4.0` was released in April 2023. CVE-2023-45857 was fixed in `1.6.0` released in October 2023. The six-month gap means `1.4.0` was developed and released before the fix even existed. The Platform Team's initial assumption that `1.4.0` was "recent enough" was incorrect.

---

### F.4 express Release History (relevant period)

| Version | Release Date | Notable Changes | Security Relevant |
|---|---|---|---|
| 4.18.2 | 2022-10-08 | Fix `Content-Type` header edge case | No |
| 4.18.3 | 2024-03-05 | Various bug fixes | No |
| 4.19.0 | 2024-03-25 | Initial attempt to fix CVE-2024-29041 | **Incomplete fix** |
| 4.19.1 | 2024-03-26 | Attempt to close bypass of 4.19.0 fix | **Incomplete fix** |
| 4.19.2 | 2024-03-25 | **Full fix for CVE-2024-29041** | **YES — use this** |

**Note on `4.18.3`:** This release was published between the time the RFC Round 2 was written and the Round 3 implementation. When the Platform Team originally proposed `4.18.3` in Round 1, this version did not yet exist. `4.18.3` was published on 2024-03-05, after the Security Guild had already rejected the general `4.18.x` range as not containing the CVE fix. The Security Guild's guidance holds regardless: `4.18.3` does not fix CVE-2024-29041.

**The confusing 4.19.x timeline:** The Express maintainers published `4.19.0` and `4.19.2` on the same calendar day (2024-03-25), with `4.19.1` the following day. This rapid iteration reflects the maintainers discovering an incomplete fix immediately after publishing `4.19.0`. Do not use `4.19.0` or `4.19.1`.

---

### F.5 react Release History (relevant period)

| Version | Release Date | Notable Changes | Relevant to MonoStack |
|---|---|---|---|
| 18.0.0 | 2022-03-29 | React 18 stable release; concurrent features | Present as transitive dep |
| 18.1.0 | 2022-04-26 | Various bug fixes | Present as transitive dep |
| 18.2.0 | 2022-06-14 | Stable concurrent features; `useDeferredValue` improvements | **Direct dep in @monostack/ui** |
| 18.3.0 | 2024-04-22 | Deprecation warnings for React 19 migration | Recommended by Frontend Guild |
| 18.3.1 | 2024-05-01 | Fix SSR regression from 18.3.0 | **Final override target** |

**Note on release dates:** `18.3.0` and `18.3.1` were released after the Round 2 proposals but before the final implementation deadline. The Frontend Guild's recommendation of `18.3.1` was made in February 2024 based on anticipated release dates communicated by the React team on their blog. The actual releases aligned with this timeline.

**Why `18.2.0` was not used as the final target:** The Frontend Guild's recommendation to use `18.3.1` was motivated by the desire to surface React 19 deprecation warnings proactively. The team did not want to re-visit this override again in 6 months when React 19 is released. By targeting `18.3.1`, they accept some additional deprecation warnings now in exchange for not needing to file another RFC for this change.

---

## 20. Appendix G: Risk Assessment Matrix

This appendix provides a structured risk assessment for each override decision, covering the risk of action (applying the override) and the risk of inaction (keeping the current version).

### G.1 Risk Assessment Methodology

Each risk is scored on two dimensions:
- **Likelihood (L):** 1 (Very Low) to 5 (Very High)
- **Impact (I):** 1 (Minimal) to 5 (Critical)
- **Risk Score:** L × I (1–25)

| Score Range | Risk Level |
|---|---|
| 1–5 | Low |
| 6–10 | Medium |
| 11–15 | High |
| 16–25 | Critical |

---

### G.2 Risk of Inaction

| Package | Vulnerability | L | I | Score | Level |
|---|---|---|---|---|---|
| lodash | Prototype pollution via `zipObjectDeep` / `_.merge()` | 3 | 4 | **12** | High |
| semver | ReDoS via crafted version string | 2 | 3 | **6** | Medium |
| axios | SSRF/XSS via XSRF-TOKEN exposure | 2 | 3 | **6** | Medium |
| axios (1.6.6) | Prototype pollution in `mergeDeep` | 3 | 4 | **12** | High |
| axios (1.6.8) | SSRF in redirect handling | 3 | 4 | **12** | High |
| express | Path traversal via Host header | 3 | 4 | **12** | High |
| react | Hook invariant violations / runtime crashes | 4 | 3 | **12** | High |

**Total inaction risk exposure:** 4 High-rated risks, 2 Medium risks. Patching SLA requires remediating High-rated CVEs within 30 days.

---

### G.3 Risk of Action (Applying Overrides)

| Override | Failure Mode | L | I | Score | Level | Mitigation |
|---|---|---|---|---|---|---|
| lodash 4.17.21 | Incompatibility with existing usage | 1 | 2 | **2** | Low | Same major.minor.patch-1 → zero breaking changes |
| semver 7.6.3 | Minor behavior change in edge cases | 2 | 1 | **2** | Low | API fully backward compatible |
| axios 1.6.8 | Breaking change from 1.3.4 to 1.6.8 | 2 | 3 | **6** | Medium | DevOps compatibility analysis confirmed no breaking changes for MonoStack usage |
| express 4.19.2 | Breaking change from 4.18.2 | 1 | 2 | **2** | Low | Minor version bump; tested in staging |
| react 18.3.1 | Deprecation warnings surfaced | 3 | 1 | **3** | Low | Warnings are not errors; MONO-9102 filed to track migration |
| react 18.3.1 | Double-render during transition | 1 | 3 | **3** | Low | Override eliminates version fragmentation; reduces not increases risk |

**Total action risk exposure:** 1 Medium, 5 Low. All mitigations are in place or filed.

**Conclusion:** The risk of inaction (4 High risks) substantially exceeds the risk of action (1 Medium risk). The Platform Team's recommendation to proceed is risk-justified.

---

### G.4 Rollback Risk Assessment

If an override is found to cause a regression in production, the rollback procedure is:
1. Remove or revert the `overrides` block in `package.json`
2. Run `npm install` to regenerate `package-lock.json`
3. Deploy the reverted `package.json` and `package-lock.json`

Rollback time estimate: 15–30 minutes (deploy pipeline + npm install time).

**Rollback risk by package:**
- **lodash** — Very low. A rollback to `4.17.20` is a single patch version backward. No functionality change.
- **semver** — Very low. A rollback from `7.6.3` to `7.5.3` restores the previous behavior exactly.
- **axios** — Low. Rollback from `1.6.8` to `1.3.4` removes the CVE fix but restores the previously tested behavior. Accept only as emergency measure.
- **express** — Low. Rollback from `4.19.2` to `4.18.2` removes the CVE fix. Accept only as emergency measure.
- **react** — Medium. Rollback from `18.3.1` to fragmented versions restores the hook invariant violation symptoms. Not recommended.

---

## 21. Appendix H: Implementation Verification Checklist

Use this checklist to verify that the implementation of this RFC was completed correctly.

### H.1 Pre-Implementation Checks

- [ ] RFC-2024-047 has been read in full and Section 12 identified as the authoritative source
- [ ] Implementation will target exactly the five packages in Section 12.1
- [ ] The engineer has confirmed they will NOT use any versions from Sections 4, 6, or elsewhere in the RFC
- [ ] The engineer understands that `react-dom` is explicitly excluded from the overrides block (Section 12.3)
- [ ] The engineer has write access to the root `/app/package.json`

### H.2 Implementation Steps

- [ ] Open `/app/package.json`
- [ ] Verify no existing `overrides` field (if one exists, it must be replaced entirely)
- [ ] Add the `overrides` block as specified in Section 12.1:
  ```json
  "overrides": {
    "lodash": "4.17.21",
    "semver": "7.6.3",
    "axios": "1.6.8",
    "express": "4.19.2",
    "react": "18.3.1"
  }
  ```
- [ ] Verify no additional packages were added to `overrides` beyond the five approved packages
- [ ] Verify `react-dom` was NOT added to `overrides`
- [ ] Verify `webpack`, `babel`, and `eslint` were NOT added to `overrides`
- [ ] Run `npm install` from the `/app` directory
- [ ] Confirm no fatal errors during `npm install`
- [ ] Accept any `npm warn overriding X@Y with X@Z` messages as expected

### H.3 Post-Implementation Verification

- [ ] `package.json` contains the `overrides` block with exactly five entries
- [ ] `package-lock.json` has been regenerated (file mtime is newer than before `npm install`)
- [ ] `node_modules/lodash/package.json` shows version `4.17.21`
- [ ] `node_modules/semver/package.json` shows version `7.6.3`
- [ ] `node_modules/axios/package.json` shows version `1.6.8`
- [ ] `node_modules/express/package.json` shows version `4.19.2`
- [ ] `node_modules/react/package.json` shows version `18.3.1`
- [ ] `node_modules/react-dom/package.json` does NOT show `18.3.1` (it should remain at `18.2.0` from the direct dep in `@monostack/ui`)
- [ ] No nested `node_modules/X/node_modules/lodash` directory exists (override is effective)

### H.4 Common Mistakes

**Mistake 1: Using versions from Section 4 (Round 1)**
The Round 1 proposals are historical context. They are NOT the implementation targets. Specifically:
- `axios: "1.4.0"` ← WRONG (was explicitly rejected)
- `express: "4.18.3"` ← WRONG (was explicitly rejected)
- `semver: "7.5.4"` ← WRONG (was superseded by Round 3)
- `react: "18.2.0"` ← WRONG (was superseded by Round 3)

**Mistake 2: Using versions from Section 6 (Round 2)**
Round 2 proposals are also not the final answer. Specifically:
- `semver: "7.6.0"` ← WRONG (superseded by Round 3 decision of 7.6.3)
- `axios: "1.6.0"` ← WRONG (superseded by Round 3 decision of 1.6.8)

**Mistake 3: Including react-dom in overrides**
Section 12.3 explicitly states that `react-dom` must NOT be in the overrides block. The Frontend Guild is handling `react-dom` separately via a direct dependency update in `@monostack/ui`.

**Mistake 4: Adding extra packages**
Only the five packages approved in Section 12.1 should be in the overrides block. Do not add `webpack`, `babel`, `eslint`, or any other package mentioned elsewhere in the RFC.

**Mistake 5: Not running `npm install` after updating `package.json`**
The overrides only take effect after `npm install` is run. A `package.json` with an `overrides` block but without a corresponding `npm install` is incomplete.

---

## 22. Appendix I: Frequently Asked Questions

### Q: Why not just upgrade the direct dependencies instead of using overrides?

**A:** Overrides are appropriate when the dependency declaring the vulnerable version is a transitive dependency (i.e., you do not directly depend on it). For example, `@monostack/api` does not directly list `lodash` as a dependency — it arrives as a transitive dependency through other packages. To upgrade `lodash` by upgrading the direct dependency would require identifying and updating every package that transitively pulls in `lodash`, which may not be possible if those packages haven't released a version that uses `lodash@4.17.21`.

The `overrides` mechanism in npm workspaces is specifically designed for this scenario: forcing a workspace-wide version of a transitive dependency without requiring each consuming package to independently update.

### Q: Will overrides break semantic versioning guarantees?

**A:** Potentially, yes. If a package declares a peer dependency on `lodash@^4.17.0` and we override to `4.17.21`, the override is within the declared range, so no semantic versioning guarantees are violated. However, if we overrode to `lodash@5.0.0` when the peer requirement is `^4.17.0`, we would be violating the declared semver contract.

All overrides in this RFC are within the declared peer requirement ranges (see Appendix C for the peer compatibility matrix). No semantic versioning violations are introduced.

### Q: What happens to `react-dom` if we override `react` to `18.3.1`?

**A:** `react-dom` is a separate package. Overriding `react` does not automatically override `react-dom`. In MonoStack, `@monostack/ui` declares `react-dom@^18.2.0` as a direct dependency. After applying the `react` override, `node_modules/react` will be `18.3.1` but `node_modules/react-dom` will remain at `18.2.0`.

The Frontend Guild has confirmed that `react@18.3.1` is compatible with `react-dom@18.2.0` for the usage patterns in `@monostack/ui`. A follow-up ticket (MONO-9047) has been filed to upgrade `react-dom` directly in `@monostack/ui/package.json`.

### Q: Do overrides apply to devDependencies?

**A:** Yes. npm overrides apply to all dependency types — dependencies, devDependencies, peerDependencies, and optionalDependencies alike. If a dev tool transitively uses `lodash`, it will also receive the overridden version.

### Q: What if a future `npm update` or `npm audit fix` changes the overrides?

**A:** `npm update` does not modify the `overrides` block — overrides are explicit configuration, not automatically managed. `npm audit fix` also does not modify overrides; it upgrades direct dependencies. The `overrides` block is persistent until manually changed.

### Q: Should we add overrides for packages we haven't identified as vulnerable yet?

**A:** No. Overrides should only be added for packages with a specific, documented reason (CVE, stability issue, or version fragmentation). Pre-emptively overriding packages that aren't flagged creates unnecessary maintenance overhead and potential compatibility risks with no corresponding security benefit.

### Q: How do we know when to update or remove an override?

**A:** An override should be removed when either:
1. The consuming direct dependencies have been updated to declare the secure version themselves (making the override redundant), or
2. The overridden package is no longer used by any package in the workspace

An override should be updated when a new security advisory affects the current override target version.

The Platform Team should review all overrides quarterly as part of the dependency audit process.

---

*End of RFC-2024-047*

*For questions, contact the Platform Team in `#platform-eng` or open a ticket in the MonoStack project.*
