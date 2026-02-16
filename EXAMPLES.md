# Copy-Paste Examples

> Ready-to-run commands for testing KB Generator

## 🚀 Windows Users - Start Here

### 1. Initial Scan
```cmd
cd C:\YOUR_PROJECT_PATH
kb-gen scan .
```

### 2. View Generated Docs
```cmd
cd .kb\flows
dir /b
type create-*.md
```

### 3. Test Impact Analysis
```cmd
REM Pick any .cs file from your project
kb-gen impact . --files src\Core\YourEntity.cs
```

### 4. Git Integration
```cmd
REM Make some code changes first, then:
kb-gen impact . --git-diff

REM Or for staged changes:
git add -A
kb-gen impact . --git-staged
```

### 5. Generate Impact Report
```cmd
kb-gen impact . --git-diff --output impact-report.md
notepad impact-report.md
```

---

## 🍎 Mac/Linux Users - Start Here

### 1. Initial Scan
```bash
cd ~/projects/your-dotnet-app
kb-gen scan .
```

### 2. View Generated Docs
```bash
cd .kb/flows
ls -1
cat create-*.md | head -50
```

### 3. Test Impact Analysis
```bash
# Pick any .cs file from your project
kb-gen impact . --files src/Core/YourEntity.cs
```

### 4. Git Integration
```bash
# Make some code changes first, then:
kb-gen impact . --git-diff

# Or for staged changes:
git add -A
kb-gen impact . --git-staged
```

### 5. Generate Impact Report
```bash
kb-gen impact . --git-diff --output impact-report.md
open impact-report.md  # macOS
# or: xdg-open impact-report.md  # Linux
```

---

## 🧪 Test With Sample Project

### Windows
```cmd
REM Using the included CleanArchitecture sample
git clone https://github.com/ardalis/CleanArchitecture.git
cd CleanArchitecture
kb-gen scan .

REM View results
explorer .kb
```

### Mac/Linux
```bash
# Using the included CleanArchitecture sample
git clone https://github.com/ardalis/CleanArchitecture.git
cd CleanArchitecture
kb-gen scan .

# View results
open .kb  # macOS
# or: nautilus .kb  # Linux with Nautilus
```

---

## 📊 Expected Output

After running `kb-gen scan .`, you should see:

```
INFO: 🔍 Starting full scan...
INFO: Found solution: YourApp with X projects
INFO: Found XXX C# files
INFO: Parsed XXX classes/types
INFO: Built dependency graph: XXX nodes, XX edges
INFO: Detected XX request flows
INFO: 📝 Generating knowledge base...
INFO: Generated SUMMARY.md
INFO: Generated XX flow documentation files
INFO: Generated 2 impact documentation files
INFO: ✅ Full scan complete — XX flow docs, 2 impact docs
```

Check your `.kb/` directory for:
- ✅ `SUMMARY.md`
- ✅ `flows/_index.md` (table of all flows)
- ✅ `flows/create-*.md` (individual flow diagrams)
- ✅ `impact/impact-map.md`

---

## 🎯 Quick Tests

### Test 1: Impact of Entity Change
**Windows:**
```cmd
REM Find your main domain entity
dir /s /b *User.cs *Order.cs *Product.cs

REM Analyze its impact
kb-gen impact . --files path\to\Entity.cs
```

**Mac/Linux:**
```bash
# Find your main domain entity
find . -name "*User.cs" -o -name "*Order.cs" -o -name "*Product.cs"

# Analyze its impact
kb-gen impact . --files path/to/Entity.cs
```

**Expected:** 🔴 CRITICAL risk with multiple flows affected

---

### Test 2: Impact of Handler Change
**Windows:**
```cmd
REM Find a handler
dir /s /b *Handler.cs

REM Analyze its impact
kb-gen impact . --files path\to\SomeHandler.cs
```

**Mac/Linux:**
```bash
# Find a handler
find . -name "*Handler.cs"

# Analyze its impact
kb-gen impact . --files path/to/SomeHandler.cs
```

**Expected:** 🟡 MEDIUM risk with 1-2 flows affected

---

### Test 3: Incremental Update
**Windows:**
```cmd
REM 1. Initial scan
kb-gen scan .

REM 2. Modify a file (any .cs file)
notepad src\SomeFile.cs
REM Make a trivial change and save

REM 3. Run incremental update
kb-gen update .
```

**Mac/Linux:**
```bash
# 1. Initial scan
kb-gen scan .

# 2. Modify a file (any .cs file)
echo "// test comment" >> src/SomeFile.cs

# 3. Run incremental update
kb-gen update .
```

**Expected:** Only regenerates affected KB docs (much faster than full scan)

---

## 🔍 Troubleshooting

### No flows detected?
**Check:**
- Your project uses CQRS pattern (Command/Query classes)
- Handlers implement `ICommandHandler<>` or `IRequestHandler<>`
- Naming convention: `CreateXxxCommand` + `CreateXxxHandler`

**Windows:**
```cmd
findstr /s /i "ICommandHandler IRequestHandler" *.cs
```

**Mac/Linux:**
```bash
grep -r "ICommandHandler\|IRequestHandler" --include="*.cs"
```

---

### Git commands failing?
**Check Git is in PATH:**

**Windows:**
```cmd
where git
REM If not found, add Git\bin to your PATH
```

**Mac/Linux:**
```bash
which git
```

---

### Path errors on Windows?
Use forward slashes (Python converts automatically):
```cmd
kb-gen scan ./MyProject
kb-gen impact . --files src/Core/Entity.cs
```

Or use quotes for paths with spaces:
```cmd
kb-gen scan "C:\My Projects\App"
```

---

## 🎓 Learning Path

1. ✅ **Start:** Run `kb-gen scan .` on your project
2. 📖 **Read:** Open `.kb/flows/_index.md` to see all flows
3. 🔍 **Explore:** Pick a flow and read its sequence diagram
4. 💥 **Test Impact:** Run `kb-gen impact . --git-diff`
5. 🚀 **Integrate:** Add to your CI/CD pipeline

---

## 📚 Next Steps

- **Full examples:** See [USAGE.md](USAGE.md)
- **Quick reference:** See [QUICKSTART.md](QUICKSTART.md)
- **Pattern details:** See [README.md](README.md)
