# Snorkel Terminus EC — npm Workspace Override Resolver

A Terminus Edition 2 task where an AI agent reads a long migration RFC and applies the correct npm `overrides` to a monorepo's root `package.json`.

## Task overview

The agent receives an npm workspace monorepo (`packages/core`, `packages/api`, `packages/ui`, `packages/cli`) and a 50k-token RFC document at `/app/docs/dependency-migration-rfc.md`. The RFC went through three rounds of review with superseded proposals, rejected versions, and scattered final decisions. The agent must identify the final approved overrides and apply them to `/app/package.json`, then run `npm install`.

## Prerequisites

Tested on Ubuntu 22.04 / 24.04. You need:

- Docker Engine 24+ ([install guide](https://docs.docker.com/engine/install/ubuntu/))
- Python 3.12 or 3.13
- Harbor CLI (`uv` recommended)
- API keys (Portkey / OpenAI-compatible endpoint)

## Setup

### 1. Install uv and Harbor

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc

uv tool install "harbor @ https://snorkel-public.s3.us-west-2.amazonaws.com/harbor/harbor-0.5.0%2Bpromptfix5-py3-none-any.whl" --python 3.13
```

### 2. Configure API keys

Add to `~/.bashrc` or `~/.zshrc`:

```bash
export OPENAI_API_KEY=<your-portkey-api-key>
export OPENAI_BASE_URL=https://api.portkey.ai/v1
```

### 3. Clone this repo

```bash
git clone https://github.com/andrey-karasev-gmail/snorkel.git
cd snorkel
```

### 4. Verify Docker is running

```bash
docker --version   # must be 24.0.0 or higher
docker ps          # must not error
```

On Ubuntu, if you get a permission error:

```bash
sudo usermod -aG docker $USER
newgrp docker
```

## Running validation

### Oracle agent (should pass — reward = 1)

The oracle runs `solution/solve.sh` which applies the correct overrides, then runs the tests.

```bash
harbor run -a oracle -p ./snorkel
```

Expected output:

```
1/1 Mean: 1.000
Reward  Count
1.0     1
```

### NOP agent (should fail — reward = 0)

The NOP agent does nothing. Tests should fail because no `overrides` block is present.

```bash
harbor run -a nop -p ./snorkel
```

Expected output:

```
1/1 Mean: 0.000
Reward  Count
0.0     1
```

## Running tests manually (without Harbor)

Build the Docker image:

```bash
docker build -t snorkel-task ./snorkel/environment
```

Run oracle + verifier together:

```bash
docker run --rm \
  -v $(pwd)/snorkel/solution:/oracle \
  -v $(pwd)/snorkel/tests:/tests \
  snorkel-task \
  bash -c "
    mkdir -p /logs/agent /logs/verifier
    chmod +x /oracle/solve.sh /tests/test.sh
    /oracle/solve.sh
    /tests/test.sh
    echo 'Reward:' && cat /logs/verifier/reward.txt
  "
```

Run tests only (without oracle — simulates NOP):

```bash
docker run --rm \
  -v $(pwd)/snorkel/tests:/tests \
  snorkel-task \
  bash -c "
    mkdir -p /logs/verifier
    chmod +x /tests/test.sh
    /tests/test.sh
    echo 'Reward:' && cat /logs/verifier/reward.txt
  "
```

## Task file structure

```
snorkel/
├── instruction.md              # Prompt shown to the AI agent
├── task.toml                   # Metadata: difficulty, category, timeouts
├── rubric.md                   # Evaluation rubric (paste into Snorkel Platform UI)
├── environment/
│   ├── Dockerfile              # node:24.4-alpine, bash, tmux, asciinema, pytest
│   ├── .dockerignore
│   └── app/
│       ├── package.json        # Workspace root — no overrides initially
│       ├── package-lock.json
│       ├── docs/
│       │   └── dependency-migration-rfc.md   # The long-context RFC
│       └── packages/
│           ├── core/package.json   # lodash@4.17.20, semver@7.5.3
│           ├── api/package.json    # express@4.18.2, axios@1.3.4
│           ├── ui/package.json     # react@18.2.0, react-dom@18.2.0
│           └── cli/package.json    # commander@11.0.0, chalk@4.1.2
├── solution/
│   └── solve.sh               # Oracle: applies final overrides + runs npm install
└── tests/
    ├── test.sh                # Entry point: runs pytest, writes reward file
    └── test_outputs.py        # 13 pytest tests verifying correct override versions
```

## What the tests check

| Test | Verifies |
|---|---|
| `test_lodash_override` | lodash pinned to `4.17.21` |
| `test_semver_override` | semver pinned to `7.6.3` (Round 3, not superseded `7.6.0`) |
| `test_axios_override` | axios pinned to `1.6.8` (Round 3, not rejected `1.4.0`) |
| `test_express_override` | express pinned to `4.19.2` (not rejected `4.18.3`) |
| `test_react_override` | react pinned to `18.3.1` |
| `test_axios_rejected_version_not_used` | axios `1.4.0` absent |
| `test_express_rejected_version_not_used` | express `4.18.3` absent |
| `test_semver_superseded_version_not_used` | semver `7.5.4` / `7.6.0` absent |
| `test_no_extra_overrides` | only 5 approved packages in overrides |
| `test_react_dom_not_overridden` | `react-dom` not in overrides (RFC §12.3) |
| `test_npm_install_completed` | `node_modules` exists |
| `test_overrides_reflected_in_lockfile` | lockfile shows new versions |
| `test_package_lock_updated` | lockfile version ≥ 3 |

## Notes on corporate network

The Dockerfile uses `public.ecr.aws/docker/library/node:24.4-alpine` with a pinned sha256 digest. If you are behind a corporate proxy that blocks Docker Hub or ECR CDN, use an internal mirror. Example for JFrog Artifactory:

```dockerfile
FROM your-registry.jfrog.io/your-repo/node:24.4-alpine@sha256:<digest>
```

Also add these workarounds for SSL inspection:

```dockerfile
RUN sed -i 's|https://dl-cdn.alpinelinux.org|http://dl-cdn.alpinelinux.org|g' /etc/apk/repositories
RUN pip3 install --trusted-host pypi.org --trusted-host files.pythonhosted.org ...
RUN npm config set strict-ssl false
```
