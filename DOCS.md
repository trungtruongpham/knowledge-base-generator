# 📚 Documentation Index

Welcome to the KB Generator documentation!

## Quick Navigation

| Document | Best For | Read Time |
|----------|----------|-----------|
| **[EXAMPLES.md](EXAMPLES.md)** | 🚀 **Start here** - Copy-paste commands | 5 min |
| **[QUICKSTART.md](QUICKSTART.md)** | Quick reference card | 2 min |
| **[USAGE.md](USAGE.md)** | Complete guide with workflows | 15 min |
| **[README.md](README.md)** | Pattern detection, architecture | 10 min |

---

## 🚀 Getting Started (Windows & Mac/Linux)

### Installation
```bash
pip install -e .
```

### First Run

**Windows:**
```cmd
kb-gen scan .\YourProject
explorer .kb
```

**Mac/Linux:**
```bash
kb-gen scan ./YourProject
open .kb  # or: ls -R .kb
```

---

## 📖 What Each Document Covers

### [EXAMPLES.md](EXAMPLES.md) - Copy-Paste Ready Commands
- ✅ Platform-specific examples (Windows CMD vs Unix Bash)
- ✅ Expected outputs for each command
- ✅ Quick tests (entity change, handler change, incremental update)
- ✅ Troubleshooting common issues
- **Best for:** Hands-on learning, immediate testing

### [QUICKSTART.md](QUICKSTART.md) - Cheat Sheet
- ✅ All commands in table format
- ✅ Risk level reference
- ✅ Output structure diagram
- ✅ Daily workflow example
- **Best for:** Quick lookup while working

### [USAGE.md](USAGE.md) - Complete Guide
- ✅ Detailed command explanations
- ✅ Real-world workflows (daily dev, code review, CI/CD)
- ✅ Git integration examples
- ✅ Performance tips
- **Best for:** Understanding all features, setting up automation

### [README.md](README.md) - Technical Details
- ✅ Pattern detection table (DDD, CQRS, Repository, etc.)
- ✅ Architecture overview
- ✅ Configuration options
- ✅ Supported frameworks
- **Best for:** Understanding how the tool works internally

---

## 🎯 Learning Path

### Beginner (5 minutes)
1. Read: [EXAMPLES.md](EXAMPLES.md) #1-3 (Installation, Initial Scan, View Docs)
2. Run: `kb-gen scan ./YourProject`
3. Explore: Open `.kb/flows/_index.md` in your browser

### Intermediate (15 minutes)
1. Read: [USAGE.md](USAGE.md) §Impact Analysis
2. Test: `kb-gen impact . --files src/Core/YourEntity.cs`
3. Test: `kb-gen impact . --git-diff`
4. Review: Generated `.kb/impact/impact-map.md`

### Advanced (30 minutes)
1. Read: [USAGE.md](USAGE.md) §CI/CD Integration
2. Setup: Pre-commit hook or CI/CD pipeline
3. Test: Incremental updates with `kb-gen update`
4. Optimize: Tune `--depth` for your codebase size

---

## 💡 FAQ

### Which file should I read first?
**[EXAMPLES.md](EXAMPLES.md)** — it has copy-paste commands for immediate testing.

### Does it work on Windows?
**Yes!** All commands work on Windows, Mac, and Linux. We provide platform-specific examples.

### What if I don't use CQRS?
The tool still generates project summaries and class documentation. Flow detection works best with CQRS patterns (Command/Query + Handler).

### How do I integrate with CI/CD?
See [USAGE.md](USAGE.md) §CI/CD Integration for GitHub Actions, Azure Pipelines, and GitLab CI examples.

---

## 🔧 Tool Overview

| Feature | Command | Output |
|---------|---------|--------|
| **Full Scan** | `kb-gen scan .` | `.kb/SUMMARY.md` + flow docs |
| **Incremental Update** | `kb-gen update .` | Regenerates only changed docs |
| **Impact Analysis** | `kb-gen impact . --files X.cs` | Terminal report or Markdown |
| **Git Integration** | `kb-gen impact . --git-diff` | Blast radius of uncommitted changes |

---

## 🌐 Cross-Platform Support

The tool is **fully cross-platform**:

### ✅ Path Handling
- Uses `pathlib.Path` (normalizes `/` and `\` automatically)
- Accepts both `./folder` and `.\folder`
- Works with network paths and UNC paths on Windows

### ✅ Git Integration
- Uses `subprocess.run()` with platform-agnostic args
- Auto-detects Git from PATH
- Works with Git Bash, CMD, PowerShell, and Unix shells

### ✅ File I/O
- UTF-8 encoding by default
- Handles Windows line endings (`\r\n`) and Unix (`\n`)
- Gracefully skips binary files

---

## 📊 Sample Output

After running `kb-gen scan .`, you'll get:

```
.kb/
├── SUMMARY.md                    # Project overview with stats
├── flows/
│   ├── _index.md                 # Table of all detected flows
│   ├── create-user.md            # Mermaid sequence diagram
│   ├── delete-order.md           # + step-by-step flow
│   └── _dependency-graph.md      # Full class dependency graph
├── impact/
│   ├── _index.md                 # Impact analysis usage guide
│   └── impact-map.md             # Per-file blast radius reference
└── .kb-state.json                # State tracking (file hashes)
```

**Example Flow Doc (`create-user.md`):**
- Mermaid sequence diagram (Endpoint → Command → Handler → Repository → Entity)
- Flow steps table with files, layers, and actions
- Dependencies (constructor-injected services)
- Cross-cutting concerns (validators, behaviors)
- Side effects (domain events)

**Example Impact Report (terminal):**
```
🔍 Impact Analysis for 1 changed file(s)
⚠️  Risk Level: 🔴 CRITICAL

🔗 Affected Classes (12)
🔄 Affected Flows (5)
📝 KB Docs to Regenerate (7)
🧪 Tests Likely Affected (8)
```

---

## 🚀 Quick Commands

```bash
# Cross-platform (works on Windows, Mac, Linux)
kb-gen scan .                          # Initial scan
kb-gen update .                        # Incremental update
kb-gen impact . --git-diff             # Impact of uncommitted changes
kb-gen impact . --files src/User.cs   # Impact of specific file
```

---

## 🛠️ Need Help?

1. **Quick test:** See [EXAMPLES.md](EXAMPLES.md) §Quick Tests
2. **Troubleshooting:** See [USAGE.md](USAGE.md) §Troubleshooting
3. **Pattern reference:** See [README.md](README.md) §Pattern Detection

---

**Happy KB Generation! 📚✨**
