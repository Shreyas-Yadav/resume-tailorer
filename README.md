# resume-tailor

A CLI tool that tailors LaTeX resumes to job postings using LLMs. It scans your project portfolio, matches the most relevant projects to a job description, rewrites bullets with quantified impact, and compiles a ready-to-send PDF.

## Features

- Fetches and parses job postings from a URL or file
- Matches your projects to the job using LLM scoring
- Rewrites project bullets, experience, and skills sections
- Compiles a polished PDF via `pdflatex`
- Supports OpenAI, Anthropic (Claude), and Google Gemini
- Parallel project enrichment and bullet generation for speed
- Optional LinkedIn recruiter message generation
- Quality review pass with iterative improvement

---

## Requirements

- Python 3.10+
- `pdflatex` (for PDF compilation) — install via [TeX Live](https://tug.org/texlive/) or [MacTeX](https://tug.org/mactex/)
- API key for at least one LLM provider

---

## Installation

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd resume-tailorer
```

### 2. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install the package

Install with your preferred LLM provider. You can install one or all:

```bash
# Anthropic (Claude)
pip3 install -e ".[claude]"

# OpenAI
pip3 install -e ".[openai]"

# Google Gemini
pip3 install -e ".[gemini]"

# All providers
pip3 install -e ".[all]"
```

### 4. Set up API keys

Copy the example environment file and fill in your keys:

```bash
cp .env.example .env
```

Edit `.env`:

```env
# Set at least one
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=...

# Default provider: openai, anthropic, or gemini
AI_PROVIDER=gemini
```

Alternatively, configure via the CLI (stored in `~/.resume-tailor.json`):

```bash
resume-tailor config set provider anthropic
resume-tailor config set model claude-sonnet-4-6
resume-tailor config set resume ~/Documents/resume.tex
resume-tailor config set projects ~/projects.md
```

---

## First-Time Setup: Build Your Project Registry

The tool needs a registry of your projects to select from. This is a one-time setup.

### Step 1 — Scan for projects

Point the scanner at one or more directories containing your code:

```bash
resume-tailor scan --dir ~/projects --dir ~/work --output ./projects.txt
```

This writes a `projects.txt` with discovered project paths.

### Step 2 — Profile projects with LLM

Enrich each project with a structured profile (tech stack, architecture, impact signals):

```bash
resume-tailor profile --input ./projects.txt --output ./projects.md
```

This creates `projects.md`, your project registry. Review and edit it as needed.

### Step 3 — Populate git remote URLs (optional)

Adds GitHub/GitLab URLs to the registry for reference:

```bash
resume-tailor remotes --projects ./projects.md
```

---

## Usage

### Tailor a resume to a job posting

From a URL:

```bash
resume-tailor tailor --job-url "https://jobs.example.com/software-engineer" --resume ~/Documents/resume.tex
```

From a saved job description file:

```bash
resume-tailor tailor --job-file ./job-posting.txt --resume ~/Documents/resume.tex
```

Output is saved to `./output/<date>/<company-position>.tex` and `.pdf`.

### Common options

| Flag | Description | Default |
|------|-------------|---------|
| `--provider, -p` | LLM provider (`openai`, `anthropic`, `gemini`) | from config |
| `--model, -m` | Model name | provider default |
| `--output-dir, -o` | Output directory | `./output` |
| `--max-projects` | Max projects to include (2–4) | `4` |
| `--pdf / --no-pdf` | Compile PDF after editing | on |
| `--tailor-experience` | Rewrite experience bullets | off |
| `--review / --no-review` | Run final quality review | on |
| `--fill-page / --no-fill-page` | Use available space for more content | off |
| `--linkedin` | Generate LinkedIn recruiter message | off |
| `--recruiter` | Recruiter's name for LinkedIn message | — |
| `--graduation` | Graduation timeline (e.g. `"May 2025"`) | — |
| `--enrich-workers` | Parallel workers for project enrichment (1–8) | `4` |
| `--bullet-workers` | Parallel workers for bullet generation (1–6) | `2` |

### Example: full run with experience tailoring and LinkedIn message

```bash
resume-tailor tailor \
  --job-url "https://jobs.example.com/backend-engineer" \
  --resume ~/Documents/resume.tex \
  --projects ./projects.md \
  --provider anthropic \
  --max-projects 3 \
  --tailor-experience \
  --fill-page \
  --linkedin \
  --recruiter "Jane" \
  --graduation "May 2026"
```

---

## Configuration

Configuration is resolved in priority order:

1. CLI flags (highest)
2. `~/.resume-tailor.json`
3. Environment variables (`.env`)
4. Built-in defaults (lowest)

### Config commands

```bash
resume-tailor config show          # Display current configuration
resume-tailor config set KEY VALUE # Set a value
resume-tailor config init          # Initialize with defaults
```

Valid keys: `provider`, `model`, `resume`, `projects`, `output_dir`

---

## Output Structure

```
output/
└── Mar-24-2026/
    ├── acme-backend-engineer.tex
    └── acme-backend-engineer.pdf
```

---

## Commands Reference

| Command | Description |
|---------|-------------|
| `resume-tailor tailor` | Run the full tailoring pipeline |
| `resume-tailor scan` | Discover project directories |
| `resume-tailor profile` | LLM-profile discovered projects |
| `resume-tailor remotes` | Add git remote URLs to the registry |
| `resume-tailor config` | Manage configuration |

---

## Troubleshooting

**`pdflatex` not found**
Install TeX Live (Linux/macOS) or MacTeX (macOS):
```bash
# macOS
brew install --cask mactex-no-gui

# Ubuntu/Debian
sudo apt-get install texlive-full
```

**API key not recognized**
Make sure your `.env` is in the project root, or export the variable directly:
```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

**`resume-tailor` command not found after install**
Ensure your virtual environment is active and the package was installed in editable mode:
```bash
source .venv/bin/activate
pip3 install -e ".[claude]"
```
