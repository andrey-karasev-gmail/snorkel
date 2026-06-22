# npm Workspace Override Resolver

A Terminus Edition 2 task where an AI agent reads a long migration RFC and applies the correct npm `overrides` to a monorepo's root `package.json`.

## Task overview

The agent receives an npm workspace monorepo (`packages/core`, `packages/api`, `packages/ui`, `packages/cli`) and a multi-section RFC at `/app/docs/dependency-migration-rfc.md`. The RFC went through three rounds of revision with superseded proposals, rejected versions, and scattered final decisions. The agent must identify the final approved overrides and apply them to `/app/package.json`, then run `npm install`.

## Prerequisites

- Docker 24+
- [Harbor CLI](https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/getting-started/quick-start)

## Install Harbor

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc
uv tool install "harbor @ https://snorkel-public.s3.us-west-2.amazonaws.com/harbor/harbor-0.5.0%2Bpromptfix5-py3-none-any.whl" --python 3.13
```

## Clone

```bash
git clone https://github.com/andrey-karasev-gmail/snorkel.git
cd snorkel
```

## Validation

### Oracle (reward = 1)

```bash
harbor run -a oracle -p ./snorkel
```

```
1/1 Mean: 1.000
Reward  Count
1.0     1
```

### NOP (reward = 0)

```bash
harbor run -a nop -p ./snorkel
```

```
1/1 Mean: 0.000
Reward  Count
0.0     1
```

## Manual Docker test

```bash
docker build -t snorkel-task ./snorkel/environment

docker run --rm \
  -v $(pwd)/snorkel/solution:/oracle \
  -v $(pwd)/snorkel/tests:/tests \
  snorkel-task \
  bash -c "
    mkdir -p /logs/agent /logs/verifier
    chmod +x /oracle/solve.sh /tests/test.sh
    /oracle/solve.sh && /tests/test.sh
    echo 'Reward:' && cat /logs/verifier/reward.txt
  "
```

## File structure

```
snorkel/
├── instruction.md
├── task.toml
├── rubric.md
├── environment/
│   ├── Dockerfile
│   ├── requirements.lock
│   ├── .dockerignore
│   └── app/
│       ├── package.json
│       ├── package-lock.json
│       ├── docs/
│       │   ├── dependency-migration-rfc.md
│       │   ├── dependency-analysis.md
│       │   ├── meeting-notes.md
│       │   └── security-audit-report.md
│       └── packages/
│           ├── core/package.json
│           ├── api/package.json
│           ├── ui/package.json
│           └── cli/package.json
├── solution/
│   └── solve.sh
└── tests/
    ├── test.sh
    └── test_outputs.py
```

## Tests

| Test | Verifies |
|---|---|
| `test_lodash_override` | lodash == `4.17.21` |
| `test_semver_override` | semver == `7.6.3` (Round 3, not superseded `7.6.0`) |
| `test_axios_override` | axios == `1.6.8` (not rejected `1.4.0`) |
| `test_express_override` | express == `4.19.2` (not rejected `4.18.3`) |
| `test_react_override` | react == `18.3.1` |
| `test_axios_rejected_version_not_used` | axios `1.4.0` absent |
| `test_express_rejected_version_not_used` | express `4.18.3` absent |
| `test_semver_superseded_version_not_used` | semver `7.5.4` / `7.6.0` absent |
| `test_no_extra_overrides` | exactly 5 packages in overrides |
| `test_react_dom_not_overridden` | `react-dom` not overridden |
| `test_npm_install_completed` | `node_modules` exists |
| `test_overrides_reflected_in_lockfile` | lockfile shows final versions |
| `test_package_lock_updated` | lockfile version ≥ 3 |
