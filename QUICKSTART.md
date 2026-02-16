# KB Generator - Quick Reference

## Installation
```bash
pip install -e .
```

## Commands

| Command | Purpose | Example (Unix) | Example (Windows) |
|---------|---------|----------------|-------------------|
| `scan` | Initial full scan | `kb-gen scan ./MyProject` | `kb-gen scan .\MyProject` |
| `update` | Incremental update | `kb-gen update ./MyProject` | `kb-gen update .\MyProject` |
| `refresh` | Force full rebuild | `kb-gen refresh ./MyProject` | `kb-gen refresh .\MyProject` |
| `impact` | Analyze change blast radius | `kb-gen impact . --files src/User.cs` | `kb-gen impact . --files src\User.cs` |

## Impact Analysis Options

```bash
# Analyze specific files
kb-gen impact ./MyProject --files src/Core/User.cs

# Analyze all uncommitted changes
kb-gen impact ./MyProject --git-diff

# Analyze staged changes
kb-gen impact ./MyProject --git-staged

# Save report to file
kb-gen impact ./MyProject --git-diff --output report.md

# Custom depth for transitive dependencies
kb-gen impact ./MyProject --files User.cs --depth 10
```

## Output Structure

```
.kb/
├── SUMMARY.md                    # Project overview
├── flows/
│   ├── _index.md                 # All flows table
│   ├── create-user.md            # Per-flow Mermaid diagram
│   └── _dependency-graph.md      # Full dependency graph
├── impact/
│   ├── _index.md                 # Impact guide
│   └── impact-map.md             # Per-file blast radius
└── .kb-state.json                # State for incremental updates
```

## Risk Levels

| Level | Icon | Meaning | Example |
|-------|------|---------|---------|
| Low | 🟢 | Leaf node change | Endpoint, test, config |
| Medium | 🟡 | Affects 1-2 flows | Single use case handler |
| High | 🟠 | Affects 3-4 flows | Shared service |
| Critical | 🔴 | Affects 5+ flows | Core entity, shared contract |

## Workflow Examples

**Daily Development:**
```bash
# 1. Initial scan
kb-gen scan ./MyProject

# 2. Before making changes
kb-gen impact ./MyProject --files src/Core/Order.cs

# 3. After coding
kb-gen update ./MyProject

# 4. Before commit
kb-gen impact ./MyProject --git-staged
```

**Pre-Commit Hook:**
```bash
#!/bin/bash
kb-gen impact . --git-staged
read -p "Continue? (y/n) " -n 1 -r
[[ ! $REPLY =~ ^[Yy]$ ]] && exit 1
```

## Tips

✅ Use `update` for speed (10x faster than `scan`)  
✅ Use `--git-diff` in pre-commit hooks  
✅ Lower `--depth` for huge codebases  
✅ Save reports with `-o report.md` for CI/CD  

📖 Full guide: [USAGE.md](USAGE.md)
