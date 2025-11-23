# Branching Strategy & CI/CD Guide

## 📋 Table of Contents
- [Branch Structure](#branch-structure)
- [Workflow](#workflow)
- [CI/CD Pipeline](#cicd-pipeline)
- [Best Practices](#best-practices)
- [Common Scenarios](#common-scenarios)

---

## 🌳 Branch Structure

### Main Branches

| Branch | Purpose | Protection | Deploy Target |
|--------|---------|-----------|---------------|
| `main` | Production code | Protected, requires PR + reviews | Production |
| `staging` | Pre-production testing | Protected, requires PR | Staging environment |
| `development` | Active development | Protected, requires PR | Development environment |

### Supporting Branches

| Type | Naming Convention | Purpose | Base Branch | Merge Into |
|------|------------------|---------|-------------|------------|
| Feature | `feature/feature-name` | New features | `development` | `development` |
| Bugfix | `bugfix/issue-name` | Bug fixes | `development` | `development` |
| Hotfix | `hotfix/critical-fix` | Critical production fixes | `main` | `main` + `development` |
| Release | `release/v1.0.0` | Release preparation | `development` | `staging` → `main` |

---

## 🔄 Workflow

### Standard Development Flow

```
feature/my-feature → development → staging → main
```

#### Step-by-Step Process:

### 1️⃣ Starting New Work

```bash
# Update your local development branch
git checkout development
git pull origin development

# Create a new feature branch
git checkout -b feature/add-job-filters

# Work on your feature
# ... make changes ...

# Commit regularly with meaningful messages
git add .
git commit -m "feat: Add salary range filter for job search"
```

### 2️⃣ Keeping Your Branch Updated

```bash
# Regularly sync with development to avoid conflicts
git checkout development
git pull origin development

git checkout feature/add-job-filters
git merge development

# Or use rebase for cleaner history (advanced)
git rebase development
```

### 3️⃣ Push and Create Pull Request

```bash
# Push your feature branch
git push origin feature/add-job-filters

# Create Pull Request on GitHub:
# - Base: development
# - Compare: feature/add-job-filters
# - Add description, link issues
# - Request reviewers
```

### 4️⃣ After PR Approval

```bash
# Merge via GitHub UI (prefer "Squash and merge")
# Delete the feature branch after merge
git checkout development
git pull origin development
git branch -d feature/add-job-filters
```

---

## 🚀 CI/CD Pipeline

### Pipeline Triggers

The CI/CD pipeline runs automatically on:
- **Push** to `main` or `development` branches
- **Pull Requests** targeting `main` or `development`

### Pipeline Stages

#### 1. **Test Stage** (Runs for all Python versions: 3.9, 3.10, 3.11)

```yaml
- Checkout code
- Setup Python environment
- Cache dependencies
- Install requirements
- Lint with flake8
- Run pytest tests
- Upload coverage reports
```

**What it checks:**
- ✅ Code syntax and style
- ✅ Unit tests pass
- ✅ Code coverage metrics
- ✅ All dependencies install correctly

#### 2. **DBT Check Stage**

```yaml
- Install DBT
- Validate DBT project structure
- Check model definitions
- Verify SQL syntax
```

**What it checks:**
- ✅ DBT project configuration
- ✅ Model file structure
- ✅ SQL compilation (syntax only)

#### 3. **Build Stage** (Only on `main` branch)

```yaml
- Build Docker images for backend
- Build Docker images for frontend
- Push to Docker Hub
- Cache layers for faster builds
```

**What it does:**
- 🐳 Creates production-ready containers
- 📦 Pushes to container registry
- 🚀 Ready for deployment

---

## ✅ Best Practices to Avoid Conflicts

### 1. **Pull Before You Push**

```bash
# Always sync before pushing
git pull origin development
git push origin feature/my-feature
```

### 2. **Keep Branches Short-Lived**

- ⏰ Aim to merge features within 2-3 days
- 🔄 Smaller PRs are easier to review and merge
- 🎯 One feature/fix per branch

### 3. **Commit Often, Push Daily**

```bash
# Make small, atomic commits
git commit -m "feat: Add filter component"
git commit -m "test: Add filter component tests"
git commit -m "docs: Update API documentation"

# Push at least once per day
git push origin feature/my-feature
```

### 4. **Write Clear Commit Messages**

Follow the Conventional Commits format:

```bash
feat: Add new job search filter
fix: Resolve pagination bug in job list
docs: Update API documentation
test: Add unit tests for resume matcher
refactor: Simplify snowflake client code
chore: Update dependencies
```

### 5. **Resolve Conflicts Locally**

```bash
# When conflicts occur during merge/rebase
git checkout development
git pull origin development
git checkout feature/my-feature
git merge development

# Fix conflicts in your editor
# Look for <<<<<<, ======, >>>>>> markers

git add .
git commit -m "merge: Resolve conflicts with development"
git push origin feature/my-feature
```

### 6. **Review Before Merging**

- 👀 Always review your own PR first
- 🧪 Test your changes locally
- 📝 Update documentation
- ✅ Ensure CI passes before requesting review

---

## 📚 Common Scenarios

### Scenario 1: Working on a Feature

```bash
# 1. Create feature branch from development
git checkout development
git pull origin development
git checkout -b feature/resume-upload

# 2. Make changes
# ... code ...

# 3. Commit and push
git add .
git commit -m "feat: Add resume upload functionality"
git push origin feature/resume-upload

# 4. Create PR to development
# 5. After approval, squash and merge
# 6. Delete feature branch
```

### Scenario 2: Critical Production Bug (Hotfix)

```bash
# 1. Create hotfix from main
git checkout main
git pull origin main
git checkout -b hotfix/fix-login-error

# 2. Fix the bug
# ... code ...

# 3. Commit and push
git add .
git commit -m "fix: Resolve login authentication error"
git push origin hotfix/fix-login-error

# 4. Create PR to main (emergency merge)
# 5. After deployment, merge into development too
git checkout development
git merge hotfix/fix-login-error
git push origin development
```

### Scenario 3: Release Preparation

```bash
# 1. Create release branch from development
git checkout development
git pull origin development
git checkout -b release/v1.2.0

# 2. Update version numbers, changelog
# ... update files ...

# 3. Create PR to staging
# 4. Test in staging environment
# 5. If tests pass, create PR to main
# 6. Tag the release
git checkout main
git tag -a v1.2.0 -m "Release version 1.2.0"
git push origin v1.2.0
```

### Scenario 4: Merge Conflict Resolution

```bash
# When you see conflict during PR
git checkout development
git pull origin development
git checkout feature/my-feature
git merge development

# Editor shows conflicts:
<<<<<<< HEAD
Your code here
=======
Conflicting code from development
>>>>>>> development

# Choose correct version or combine both
# Remove conflict markers

git add .
git commit -m "merge: Resolve conflicts with development"
git push origin feature/my-feature

# PR will update automatically
```

### Scenario 5: Update Branch with Latest Changes

```bash
# Method 1: Merge (preserves history)
git checkout feature/my-feature
git merge development
git push origin feature/my-feature

# Method 2: Rebase (cleaner history, advanced)
git checkout feature/my-feature
git rebase development
# Fix any conflicts if they occur
git push origin feature/my-feature --force-with-lease
```

---

## 🛡️ GitHub Branch Protection Rules

### Recommended Settings for `main`:

- ✅ Require pull request before merging
- ✅ Require 1-2 approvals
- ✅ Dismiss stale reviews
- ✅ Require status checks (CI must pass)
- ✅ Require branches to be up to date
- ✅ Require conversation resolution
- ✅ Do not allow force pushes
- ✅ Do not allow deletions

### Recommended Settings for `development`:

- ✅ Require pull request before merging
- ✅ Require 1 approval
- ✅ Require status checks (CI must pass)
- ✅ Do not allow force pushes

---

## 🔍 CI/CD Troubleshooting

### Pipeline Fails on Tests

```bash
# Run tests locally first
pytest tests/ -v

# Fix failing tests
# Commit and push
git add .
git commit -m "fix: Resolve failing unit tests"
git push
```

### Pipeline Fails on Linting

```bash
# Run flake8 locally
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics

# Fix linting issues
# Commit and push
```

### DBT Check Fails

```bash
# Test DBT locally
cd dbt
dbt debug
dbt compile

# Fix DBT models
# Commit and push
```

### Docker Build Fails

```bash
# Test Docker build locally
docker build -t test-backend ./backend
docker build -t test-frontend ./frontend

# Fix Dockerfile issues
# Commit and push
```

---

## 📊 Git Flow Visualization

```
main         ─────●─────────────●─────────●────────→ (Production)
                   │             │         │
                   │             │    ┌────┘
staging      ──────┼─────────────●────┤─────●───────→ (Pre-prod)
                   │             │    │     │
                   │        ┌────┘    │     │
development  ──────●────●───●────●────┴─────┴───●───→ (Dev)
                   │    │        │              │
                   │    │        │              │
feature/*     ─────┴────┘        └──────────────┘
```

---

## 🎯 Quick Reference Commands

```bash
# Start new feature
git checkout development && git pull
git checkout -b feature/name

# Update your branch
git checkout development && git pull
git checkout feature/name && git merge development

# Push changes
git add . && git commit -m "message"
git push origin feature/name

# Clean up after merge
git checkout development && git pull
git branch -d feature/name

# Emergency hotfix
git checkout main && git pull
git checkout -b hotfix/name
# ... fix and push ...

# View all branches
git branch -a

# Delete remote branch
git push origin --delete feature/name
```

---

## 📞 Getting Help

- **Merge Conflicts?** Ask a senior developer for help
- **CI/CD Failing?** Check the logs in GitHub Actions
- **Unsure About Branching?** Follow the examples above
- **Need Code Review?** Tag team members in the PR

---

**Remember:** When in doubt, create a branch, commit often, and ask for help! 🚀
