# Skill: Git Workflow & Branch Management

## Overview

All code changes in **VeggaFresh Backend** follow a strict branch-based workflow.
**Never push directly to `main`.** Every change — no matter how small — must go through a dedicated branch and be merged via a Pull Request.

---

## 1. Branch Naming Convention

| Change Type | Pattern | Example |
|---|---|---|
| New feature | `feature/<short-description>` | `feature/order-filters` |
| Bug fix | `fix/<short-description>` | `fix/order-shuffle` |
| Urgent production fix | `hotfix/<short-description>` | `hotfix/payment-crash` |
| Chore / docs / refactor | `chore/<short-description>` | `chore/update-claude-md` |

Keep branch names lowercase with hyphens. Be descriptive but concise.

---

## 2. Step-by-Step Push Process

Follow these steps **every time** you push code changes:

```bash
# Step 1: Start from an up-to-date main
git checkout main
git pull origin main

# Step 2: Create your feature/fix branch
git checkout -b feature/<description>

# Step 3: Make your code changes, then stage them
git add <specific-files>        # prefer specific files over `git add .`

# Step 4: Commit with a meaningful message
git commit -m "feat: short description of what changed"

# Step 5: Push the branch to GitHub (NOT main)
git push origin feature/<description>

# Step 6: Open a Pull Request on GitHub
# https://github.com/Susanthvocolis/Veggafresh_backend/pull/new/feature/<description>
```

> **Rule:** `main` only receives code through Pull Requests after local testing is confirmed.

---

## 3. Commit Message Format

```
type: short description (max ~72 characters)

- Optional bullet for more detail
- Another detail if needed
```

### Allowed Types

| Type | When to use |
|---|---|
| `feat` | New feature or endpoint |
| `fix` | Bug fix |
| `hotfix` | Urgent production fix |
| `chore` | Maintenance, config, docs, refactor |
| `docs` | Documentation only |
| `refactor` | Code restructure with no behaviour change |
| `test` | Adding or updating tests |

### Examples

```bash
git commit -m "feat: add filters and sorting to GET /api/v1/orders/"
git commit -m "fix: add order_by('-created_at') to prevent order shuffling"
git commit -m "chore: add git workflow rules to CLAUDE.md and skills/"
git commit -m "feat: add AdminOrderSerializer without product_image for admin API"
```

---

## 4. Reverting a Commit from `main`

If a commit was accidentally pushed to `main` and needs to be moved to a branch:

```bash
# Step 1: Create a new branch from the current state of main (saves the commit)
git checkout -b feature/<description>
git push origin feature/<description>

# Step 2: Go back to main and revert the accidental commit
git checkout main
git revert <commit-hash> --no-edit

# Step 3: Push the cleaned-up main
git push origin main
```

> Use `git revert` (not `git reset`) because `main` is already pushed to remote.
> `git revert` creates a new "undo" commit safely without rewriting history.

---

## 5. Checking What's in a Commit

```bash
# View recent commits
git log --oneline -10

# View exact files changed in a specific commit
git show <commit-hash> --stat

# View full diff of a commit
git show <commit-hash>
```

---

## 6. Active Branch Overview (VeggaFresh)

| Branch | Purpose |
|---|---|
| `main` | Production — only stable, tested code |
| `feature/filters-sorting` | Filters, search, sorting for `/api/v1/orders/` |
| `feature/pagination` | Pagination + `product_image` removal for admin API |
| `chore/update-claude-md-git-workflow` | Git workflow docs update |

---

## 7. Pull Request Checklist

Before merging a branch into `main`:

- [ ] Tested locally (dev server running, API tested via Postman/browser)
- [ ] No debug code or print statements left in
- [ ] Commit messages are clean and descriptive
- [ ] No unrelated files staged (check `git status` before committing)
- [ ] Branch is up to date with `main` (`git pull origin main` before merging)
