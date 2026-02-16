# 🚀 Getting Started - Terminal Setup

## Why `kb-gen` isn't found?

The `kb-gen` command is installed in the **project's virtual environment** (`venv/`), not globally. You need to activate the virtual environment in each new terminal session.

---

## ✅ Solution: Activate Virtual Environment

### Every time you open a new terminal:

```bash
cd /Users/trungtruongpham/projects/knowledge-base-generator
source venv/bin/activate
```

**You'll see your prompt change to:**
```bash
(venv) user@machine knowledge-base-generator %
```

**Now `kb-gen` works:**
```bash
kb-gen --version
# kb-gen, version 0.1.0
```

---

## 🎯 Quick Commands (After Activating venv)

```bash
# Full scan
kb-gen scan ./CleanArchitecture

# Impact analysis
kb-gen impact ./CleanArchitecture --files src/Core/Entity.cs

# Git integration
kb-gen impact ./CleanArchitecture --git-diff

# Help
kb-gen --help
kb-gen impact --help
```

---

## 🔄 One-Time Global Install (Optional)

If you want `kb-gen` available **everywhere** without activating venv:

### Option 1: Install with pipx (Recommended)
```bash
# Install pipx first (if not already installed)
brew install pipx  # macOS
# or: python3 -m pip install --user pipx

# Then install kb-gen globally
pipx install -e /Users/trungtruongpham/projects/knowledge-base-generator

# Now kb-gen works everywhere
kb-gen --version
```

### Option 2: Add venv/bin to PATH
Add to your `~/.zshrc` or `~/.bashrc`:

```bash
export PATH="/Users/trungtruongpham/projects/knowledge-base-generator/venv/bin:$PATH"
```

Then reload:
```bash
source ~/.zshrc
```

---

## 🪟 Windows Users

### Activate Virtual Environment (CMD)
```cmd
cd C:\path\to\knowledge-base-generator
venv\Scripts\activate.bat
```

### Activate Virtual Environment (PowerShell)
```powershell
cd C:\path\to\knowledge-base-generator
.\venv\Scripts\Activate.ps1
```

If you get an execution policy error:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

## 📝 Troubleshooting

### "pip: command not found"
**Cause:** Virtual environment not activated  
**Fix:**
```bash
source venv/bin/activate
```

### "kb-gen: command not found" (even after activating)
**Cause:** Package not installed in venv  
**Fix:**
```bash
source venv/bin/activate
pip install -e .
```

### "venv not found"
**Cause:** Virtual environment doesn't exist  
**Fix:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

---

## 🎓 Workflow Recommendation

### Daily Development
```bash
# Terminal 1: Open and activate once
cd ~/projects/knowledge-base-generator
source venv/bin/activate

# Now run kb-gen commands
kb-gen scan ./CleanArchitecture
kb-gen impact ./CleanArchitecture --git-diff
```

### VS Code Integrated Terminal
VS Code can auto-activate the venv for you:

1. Open Command Palette (`Cmd+Shift+P`)
2. Search: "Python: Select Interpreter"
3. Choose: `./venv/bin/python`
4. New terminals will auto-activate the venv

---

## ✨ Quick Test

```bash
# 1. Activate venv
source venv/bin/activate

# 2. Verify it works
kb-gen --version

# 3. Run a scan
kb-gen scan ./CleanArchitecture

# 4. View results
ls -la CleanArchitecture/.kb/
```

---

**Remember:** 🔑 **Always activate venv first:** `source venv/bin/activate`
