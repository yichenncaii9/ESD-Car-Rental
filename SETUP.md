# Team Setup Guide

## Prerequisites

- Docker Desktop installed and running
- Git access to this repo

## Team Lead — One-time Setup (done once per project lifetime)

1. **Create two Firebase Auth test accounts** in Firebase Console → Authentication → Add User:
   - `testdriver_a@test.com` / [shared password]
   - `testdriver_b@test.com` / [shared password]

2. **Copy their UIDs** (Firebase Console → Authentication → Users → UID column) into `seed_data.py`:
   ```python
   TEST_ACCOUNT_A_UID = "paste-uid-here"
   TEST_ACCOUNT_B_UID = "paste-uid-here"
   ```

3. **Run the seeder once** (requires `firebase-service-account.json` at project root):
   ```bash
   pip install firebase-admin
   python seed_data.py
   ```
   This seeds 10 vehicles and driver profiles for both test accounts. Safe to re-run — already-existing documents are skipped.

4. **Share with teammates** (via secure channel, NOT committed to git):
   - `firebase-service-account.json`
   - `.env` (all API keys pre-filled)
   - The two test account credentials

---

## Teammates — Getting Started

```bash
# 1. Clone the repo
git clone <repo-url>
cd ESDProj

# 2. Drop these files into ESDProj/ root (get from team lead):
#    - firebase-service-account.json
#    - .env

# 3. Build and start all services
docker compose up --build

# 4. Open the app
open http://localhost:8080

# 5. Log in with one of the shared test accounts
#    testdriver_a@test.com  or  testdriver_b@test.com
```

**Do NOT run `npm install` or `python seed_data.py` — Docker handles dependencies, and data is already seeded in the shared Firestore.**

---

## Start & Tear Down (CLI)

### After `git pull` — rebuild everything and redeploy (k8s)

```bash
# One command: rebuilds all images (with k8s ports) + applies manifests + restarts pods
./scripts/deploy-k8s.sh
```

### After `git pull` — manifests only changed, no code changes

```bash
# Skip rebuild, just re-apply manifests and restart
./scripts/deploy-k8s.sh --apply
```

### First time / fresh start

```bash
./scripts/deploy-k8s.sh   # builds + deploys everything
kubectl get pods -w        # watch pods come up
```

### Stop (keep cluster, free resources)

```bash
kubectl scale deployment --all --replicas=0
kubectl scale statefulset --all --replicas=0
```

### Resume after scaling down

```bash
kubectl scale deployment --all --replicas=1
kubectl scale statefulset --all --replicas=1
```

### Full tear down (removes all deployed resources)

```bash
kubectl delete -f k8s/ --recursive
```

---

## Data Model

- Single shared Firestore database (one Firebase project, owned by team lead)
- All teammates read/write the same data — if Account A books a car, Account B sees it unavailable on next page load
- `uid` field on driver/booking documents ties records to the Firebase Auth user

## Services & Ports

| Service | Docker Compose | Kubernetes (k8s) |
|---|---|---|
| Frontend (Vue.js) | 8080 | 30080 (NodePort) |
| Kong API Gateway | 8000 | 30000 (NodePort) |
| Kong Admin API | 8001 | 30001 (NodePort) |
| WebSocket server | 6100 | ClusterIP only |
| RabbitMQ admin | 15672 | ClusterIP only |

> **Most teammates use Docker Compose** — use the left column. Kubernetes ports apply only if you're running the k8s manifests locally.

---

## Git — Contributing to the Project

### First-time setup

```bash
# Tell git who you are (one-time, on your machine)
git config --global user.name "Your Name"
git config --global user.email "your@email.com"
```

### Everyday workflow

```bash
# 1. Before you start any work — pull the latest changes from the team
git pull origin main

# 2. Create a branch for your feature or fix
#    Use a short descriptive name, e.g. fix-cancel-booking or feat-profile-page
git checkout -b your-branch-name

# 3. Make your changes, then check what you've modified
git status          # shows which files changed
git diff            # shows the actual line changes

# 4. Stage the files you want to commit
git add filename.py          # add one file
git add .                    # add everything (use carefully)

# 5. Commit with a clear message describing what you did
git commit -m "fix: correct error message on cancel booking"

# 6. Push your branch to GitHub
git push origin your-branch-name

# 7. Open a Pull Request on GitHub so the team can review before merging to main
#    GitHub → your repo → "Compare & pull request"
```

### Syncing if main has moved ahead

```bash
# While on your branch, pull in the latest main
git fetch origin
git rebase origin/main

# If there are conflicts, git will tell you which files to fix.
# Open those files, resolve the conflict markers (<<<<<<<), then:
git add the-fixed-file.py
git rebase --continue
```

### Useful one-liners

```bash
git log --oneline        # see recent commits in one line each
git stash                # temporarily shelve your uncommitted changes
git stash pop            # bring them back
git checkout main        # switch back to main branch
git branch               # list all your local branches
git branch -d old-branch # delete a branch you're done with
```

### Commit message conventions used in this project

```
feat: add new feature
fix: bug fix
docs: documentation only
refactor: code change with no feature/fix
chore: dependency updates, config changes
```
