# KB Generator - Usage Guide

> Cross-platform .NET Knowledge Base Generator with flow analysis and impact tracking

## Installation

```bash
# Clone and install
git clone <repo-url>
cd knowledge-base-generator
pip install -e .
```

## Quick Start

### 1️⃣ Initial Scan

Generate a complete knowledge base from your .NET solution:

**Unix/Mac:**
```bash
kb-gen scan ./MyProject
kb-gen scan ~/projects/MyDotNetApp
kb-gen scan ../CleanArchitecture -o .kb-custom
```

**Windows:**
```cmd
kb-gen scan .\MyProject
kb-gen scan C:\Projects\MyDotNetApp
kb-gen scan ..\CleanArchitecture -o .kb-custom
```

**Output:**
```
.kb/
├── SUMMARY.md                    # Project overview
├── flows/
│   ├── _index.md                 # All request flows
│   ├── create-user.md            # Per-flow sequence diagrams
│   ├── delete-order.md
│   └── _dependency-graph.md      # Full class dependency graph
├── impact/
│   ├── _index.md                 # Impact analysis guide
│   └── impact-map.md             # Per-file blast radius reference
└── .kb-state.json                # State tracking for incremental updates
```

---

## Core Commands

### `scan` - Initial Full Scan

**Purpose:** First-time knowledge base generation

**Unix/Mac:**
```bash
# Basic scan
kb-gen scan ./MyProject

# Custom output directory
kb-gen scan ./MyProject --output-dir .documentation

# Verbose mode (detailed logging)
kb-gen --verbose scan ./MyProject
```

**Windows:**
```cmd
kb-gen scan .\MyProject
kb-gen scan .\MyProject --output-dir .documentation
kb-gen --verbose scan .\MyProject
```

---

### `update` - Incremental Update

**Purpose:** Fast incremental updates (only regenerates affected KB docs)

**Unix/Mac:**
```bash
# After modifying code, update the KB
kb-gen update ./MyProject

# With custom output directory
kb-gen update ./MyProject -o .docs
```

**Windows:**
```cmd
kb-gen update .\MyProject
kb-gen update .\MyProject -o .docs
```

**How it works:**
- Detects changed files via file hash comparison
- Runs impact analysis to identify affected flows/docs
- Regenerates only the necessary KB files (not a full rescan)

---

### `refresh` - Force Full Rebuild

**Purpose:** Delete state and regenerate everything from scratch

**Unix/Mac:**
```bash
kb-gen refresh ./MyProject
```

**Windows:**
```cmd
kb-gen refresh .\MyProject
```

**Use when:**
- KB output is corrupted
- State file is out of sync
- You want to reset everything

---

### `impact` - Change Impact Analysis 🔥

**Purpose:** Predict the blast radius of code changes before committing

#### Analyze Specific Files

**Unix/Mac:**
```bash
# Single file
kb-gen impact ./MyProject --files src/Core/User.cs

# Multiple files
kb-gen impact ./MyProject \
  --files src/Core/User.cs \
  --files src/UseCases/CreateUserHandler.cs

# Relative paths work too
cd MyProject
kb-gen impact . -f src/Core/User.cs -f src/UseCases/Handler.cs
```

**Windows:**
```cmd
REM Single file
kb-gen impact .\MyProject --files src\Core\User.cs

REM Multiple files
kb-gen impact .\MyProject ^
  --files src\Core\User.cs ^
  --files src\UseCases\CreateUserHandler.cs

REM Relative paths
cd MyProject
kb-gen impact . -f src\Core\User.cs -f src\UseCases\Handler.cs
```

**Output:**
```
🔍 Impact Analysis for 1 changed file(s)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📄 Changed: src/Core/User.cs

⚠️  Risk Level: 🔴 CRITICAL

🔗 Affected Classes (15):
   ├── DIRECT: UserService (injects User)
   ├── DIRECT: CreateUserHandler (uses User)
   └── INDIRECT: UserValidator (validates UserDto)
   ...

🔄 Affected Flows (7):
   ├── Create User
   ├── Update User Profile
   └── Delete User Account
   ...

📝 KB Docs to Regenerate (9):
   ├── SUMMARY.md
   ├── flows/create-user.md
   └── flows/update-user-profile.md
   ...

🧪 Tests Likely Affected (12):
   └── UserServiceTests (tests class: UserService)
   ...
```

---

#### Git Integration

**Unix/Mac:**
```bash
# Analyze all uncommitted changes
kb-gen impact ./MyProject --git-diff

# Analyze staged changes only
kb-gen impact ./MyProject --git-staged

# Save report to file
kb-gen impact ./MyProject --git-diff --output impact-report.md
```

**Windows:**
```cmd
REM Analyze all uncommitted changes
kb-gen impact .\MyProject --git-diff

REM Analyze staged changes only
kb-gen impact .\MyProject --git-staged

REM Save report to file
kb-gen impact .\MyProject --git-diff --output impact-report.md
```

---

#### Advanced Options

```bash
# Custom transitive dependency depth (default: 5)
kb-gen impact ./MyProject --files User.cs --depth 10

# Generate Markdown report instead of terminal output
kb-gen impact ./MyProject --git-diff -o report.md

# Verbose mode with detailed graph building logs
kb-gen --verbose impact ./MyProject --git-diff
```

---

## Real-World Workflows

### 📅 Daily Development Workflow

**Unix/Mac:**
```bash
# 1. Morning: Generate initial KB
kb-gen scan ~/projects/MyApp

# 2. Before making changes: Check impact
kb-gen impact ~/projects/MyApp --files src/Core/Order.cs

# 3. After coding: Update KB incrementally
kb-gen update ~/projects/MyApp

# 4. Before committing: Verify impact of all changes
kb-gen impact ~/projects/MyApp --git-staged
```

**Windows:**
```cmd
REM 1. Morning: Generate initial KB
kb-gen scan C:\projects\MyApp

REM 2. Before making changes: Check impact
kb-gen impact C:\projects\MyApp --files src\Core\Order.cs

REM 3. After coding: Update KB incrementally
kb-gen update C:\projects\MyApp

REM 4. Before committing: Verify impact of all changes
kb-gen impact C:\projects\MyApp --git-staged
```

---

### 🔍 Code Review Workflow

**Unix/Mac:**
```bash
# Reviewer: Assess PR impact
git fetch origin pull/123/head:pr-123
git checkout pr-123
kb-gen impact . --git-diff main --output pr-123-impact.md

# Share the Markdown report with the team
```

**Windows:**
```cmd
REM Reviewer: Assess PR impact
git fetch origin pull/123/head:pr-123
git checkout pr-123
kb-gen impact . --git-diff main --output pr-123-impact.md
```

---

### 🚀 CI/CD Integration

**GitHub Actions (Unix runners):**
```yaml
name: KB Impact Analysis
on: [pull_request]
jobs:
  impact:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - run: pip install -e .
      - run: kb-gen impact . --git-diff origin/main --output impact.md
      - uses: actions/upload-artifact@v3
        with:
          name: impact-report
          path: impact.md
```

**Azure Pipelines (Windows runners):**
```yaml
trigger:
  - main
pool:
  vmImage: 'windows-latest'
steps:
  - task: UsePythonVersion@0
    inputs:
      versionSpec: '3.10'
  - script: pip install -e .
  - script: kb-gen impact . --git-diff origin/main --output impact.md
  - task: PublishBuildArtifacts@1
    inputs:
      pathToPublish: 'impact.md'
      artifactName: 'impact-report'
```

---

### 🧪 Pre-Commit Hook

**Unix/Mac (.git/hooks/pre-commit):**
```bash
#!/bin/bash
echo "🔍 Running KB impact analysis..."
kb-gen impact . --git-staged --depth 3

read -p "Continue with commit? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
fi
```

**Windows (.git/hooks/pre-commit.ps1):**
```powershell
Write-Host "🔍 Running KB impact analysis..." -ForegroundColor Cyan
kb-gen impact . --git-staged --depth 3

$response = Read-Host "Continue with commit? (y/n)"
if ($response -ne 'y') {
    exit 1
}
```

---

## Output Exploration

### Flow Documentation

**Example: `flows/create-user.md`**

```markdown
---
title: Create User
flow_type: Command
http_method: POST
route: /api/users
aggregate: User
---

# Create User

> **POST /api/users**

## 🔄 Sequence Diagram

```mermaid
sequenceDiagram
    participant CreateUserEndpoint
    participant CreateUserCommand
    participant CreateUserHandler
    participant IRepository<User>
    participant User

    CreateUserEndpoint->>CreateUserCommand: dispatches
    CreateUserCommand->>CreateUserHandler: handles command
    CreateUserHandler->>IRepository<User>: persists/retrieves data
    IRepository<User>->>User: domain entity
```

## 📋 Flow Steps

| # | Layer | Class | Action | File |
|---|-------|-------|--------|------|
| 1 | Web | CreateUserEndpoint | receives HTTP POST | Endpoints/CreateUser.cs |
| 2 | Application | CreateUserCommand | CQRS command message | Commands/CreateUserCommand.cs |
| 3 | Application | CreateUserHandler | handles command | Handlers/CreateUserHandler.cs |
| 4 | Infrastructure | IRepository<User> | persists/retrieves data | Repository.cs |
| 5 | Core | User | domain entity | Aggregates/User.cs |

## 🛡️ Cross-Cutting

- FluentValidation: CreateUserValidator
```

---

### Impact Map

**Example: `impact/impact-map.md`**

Shows per-file blast radius for every significant source file:

```markdown
## Core Layer (High Impact)

### User.cs
**Role:** entity
**Layer:** Core

| Impact Type | Affected | Level |
|-------------|----------|-------|
| Classes | UserService, UserValidator, CreateUserHandler | Direct |
| Flows | Create User, Update User, Delete User | Direct |
| Risk | 🔴 **CRITICAL** | 3 flow(s) affected |
```

---

## Performance Tips

1. **Use `update` instead of `scan`** after initial generation
2. **Limit impact depth** for large codebases: `--depth 3`
3. **Run `refresh` only when needed** (state corruption)
4. **Use `--git-staged`** in pre-commit hooks for speed

---

## Troubleshooting

### Windows Path Issues

If you encounter path errors on Windows:

```cmd
REM Use forward slashes (Python handles conversion)
kb-gen scan ./MyProject

REM Or use raw strings in scripts
kb-gen scan "C:\Projects\My App\Solution"
```

### Git Not Found

Ensure Git is in your PATH:

**Windows:**
```cmd
where git
REM If not found, add Git to PATH or use absolute paths
```

**Unix/Mac:**
```bash
which git
```

### No Flows Detected

If no flows are detected:
- Ensure your codebase follows CQRS patterns (Command/Query + Handler)
- Check that handler classes implement `ICommandHandler` or `IRequestHandler`
- Verify naming conventions: `XxxCommand` + `XxxHandler`

---

## Next Steps

- ✅ Run your first scan: `kb-gen scan ./MyProject`
- 📖 Explore generated docs in `.kb/flows/`
- 🔍 Try impact analysis: `kb-gen impact . --git-diff`
- 🚀 Integrate into CI/CD pipeline
- 📚 Read the full [README](README.md) for pattern detection details
