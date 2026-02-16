# .NET Knowledge Base Generator

Generate LLM-friendly knowledge bases from .NET/C# projects. Automatically scans your codebase and produces structured Markdown documentation that's perfect for feeding into AI assistants like Claude, GPT, or your favorite RAG pipeline.

## 🌟 Features

- **📊 Multi-layered KB**: Condensed summary + detailed per-concept documentation
- **🔄 Incremental Updates**: Only re-processes changed files (via SHA256 tracking)
- **🎯 Pattern Detection**: Detects CQRS, DDD Aggregates, Repository, Specification, FastEndpoints, EF Configuration, Domain Events
- **📦 Solution-aware**: Parses `.sln`, `.slnx`, and `.csproj` files to understand project structure
- **🌳 Tree-sitter Powered**: Accurate C# parsing without needing the .NET SDK installed
- **⚡ Fast**: Typically scans medium-sized solutions (100 files) in under 30 seconds

## 📦 Installation

### Prerequisites

- Python 3.11 or higher

### Install

```bash
# Clone the repository
git clone <your-repo-url>
cd knowledge-base-generator

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in editable mode
pip install -e .
```

## 🚀 Quick Start

### 1. Scan a .NET Project

```bash
kb-gen scan ./path/to/your/dotnet/solution
```

This will:
- Parse all `.cs`, `.csproj`, and `.sln` files
- Detect architectural patterns
- Generate `.kb/` directory with knowledge base files
- Save state for incremental updates

### 2. Check the Output

```bash
tree ./path/to/your/dotnet/solution/.kb

# Example output:
# .kb/
# ├── SUMMARY.md              # Condensed overview
# └── .kb-state.json          # State file for incremental updates
```

### 3. Incremental Update

After making changes to your code:

```bash
kb-gen update ./path/to/your/dotnet/solution
```

Only changed files will be re-processed!

### 4. Force Refresh

To force a complete re-scan:

```bash
kb-gen refresh ./path/to/your/dotnet/solution
```

## 📖 CLI Reference

### `kb-gen scan`

Perform a full initial scan of a .NET project.

```bash
kb-gen scan <path> [options]
```

**Options:**
- `-o, --output-dir TEXT`: Output directory for KB files (default: `.kb`)

**Example:**
```bash
kb-gen --verbose scan ./CleanArchitecture -o docs/knowledge-base
```

### `kb-gen update`

Incrementally update the knowledge base (only re-process changed files).

```bash
kb-gen update <path> [options]
```

**Options:**
- `-o, --output-dir TEXT`: Output directory for KB files (default: `.kb`)

**Example:**
```bash
kb-gen update ./CleanArchitecture
```

### `kb-gen refresh`

Force full re-scan (deletes state and regenerates everything).

```bash
kb-gen refresh <path> [options]
```

## 📂 Output Format

### SUMMARY.md

A condensed overview perfect for pasting into LLM context windows:

- **Project Structure**: All projects with types (Domain, Infrastructure, Web, Test)
- **Domain Model**: Aggregates, entities, value objects with key properties
- **Use Cases**: Commands and Queries with their handlers
- **Technology Stack**: NuGet packages and versions

**Example:**
```markdown
# Clean.Architecture

> **Knowledge Base Summary** — Generated from .NET solution

**Total Projects:** 9
**Total Classes:** 382
**Domain Aggregates:** 1
**Use Cases:** 8

## 📦 Project Structure

| Project | Type | Framework |
|---------|------|-----------|
| Clean.Architecture.Core | Domain/Core | net10.0 |
| Clean.Architecture.Web | Web/API | net10.0 |
...
```

## 🎯 Supported Patterns

The KB generator automatically detects and documents:

| Pattern | Detection Heuristic |
|---------|---------------------|
| **Aggregate Root** | Implements `IAggregateRoot` |
| **Value Object** | Vogen attribute, extends `ValueObject`, or simple record |
| **Domain Event** | Name ends with "Event" or implements event interface |
| **Command (CQRS)** | Implements `ICommand<T>` or name ends with "Command" |
| **Query (CQRS)** | Implements `IQuery<T>` or name ends with "Query" |
| **Handler** | Implements `ICommandHandler<T>` or `IQueryHandler<T>` |
| **Repository** | Implements `IRepository<T>` or extends repository base |
| **Specification** | Extends `Specification<T>` |
| **FastEndpoint** | Extends `Endpoint<TRequest, TResponse>` |
| **EF Configuration** | Implements `IEntityTypeConfiguration<T>` |
| **DTO** | Record with only properties, or name ends with DTO/Request/Response |

## 🔧 Configuration

Create `.kb-config.yaml` in your project root (optional):

```yaml
# Exclude projects matching these patterns
exclude_projects:
  - "*.Tests"
  - "*.AspireHost"

# Exclude file paths matching these patterns
exclude_paths:
  - "**/Migrations/**"
  - "**/obj/**"
  - "**/bin/**"

# Output directory
output_dir: ".kb"

# Include code snippets in KB
include_source_snippets: true

# Truncate long method bodies
max_method_body_lines: 10
```

## 🧪 Example: CleanArchitecture

Scanning the [Ardalis CleanArchitecture](https://github.com/ardalis/CleanArchitecture) template:

```bash
kb-gen --verbose scan ./CleanArchitecture
```

**Output:**
```
INFO: Starting full scan of: CleanArchitecture
INFO: Found solution: Clean.Architecture with 9 projects  
INFO: Found 357 C# files
INFO: Parsed 382 classes/types
INFO: Found 1 domain aggregates
INFO: Found 8 use cases
INFO: ✅ Knowledge base generated at: CleanArchitecture/.kb
```

**Generated Files:**
- `SUMMARY.md`: Project overview with all aggregates, use cases, and tech stack

## 💡 Use Cases

### 1. Feed Context to AI Assistants

Paste `SUMMARY.md` into Claude/GPT when asking questions about your codebase:

```
I have a .NET project with this structure:
[paste SUMMARY.md]

How should I add a new aggregate for Order management?
```

### 2. Onboarding Documentation

Use the KB as living documentation for new team members.

### 3. RAG Pipeline

Feed the KB files into a vector database for semantic search over your codebase.

### 4. CI/CD Integration

Add to your build pipeline to keep documentation up-to-date:

```yaml
# GitHub Actions example
- name: Update Knowledge Base
  run: |
    kb-gen update . --output-dir docs/kb
    git add docs/kb
    git commit -m "Update knowledge base"
```

## 🛠️ Development

### Run Tests

```bash
pytest
```

### Install Dev Dependencies

```bash
pip install -e ".[dev]"
```

## 📋 Roadmap

- [ ] Generate detailed per-aggregate Markdown files
- [ ] Generate use-case flow diagrams (Mermaid)
- [ ] API endpoint documentation with route tables
- [ ] Database schema visualization
- [ ] Cross-reference links between KB documents
- [ ] Support for other .NET frameworks (VB.NET)
- [ ] JSON export for RAG pipelines

## 🤝 Contributing

Contributions welcome! Please open an issue or PR.

## 📄 License

MIT

## 🙏 Acknowledgments

- Built with [tree-sitter](https://tree-sitter.github.io/tree-sitter/)
- Inspired by the [Ardalis CleanArchitecture](https://github.com/ardalis/CleanArchitecture) template
