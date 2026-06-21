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

*End of RFC-2024-047*

*For questions, contact the Platform Team in `#platform-eng` or open a ticket in the MonoStack project.*
