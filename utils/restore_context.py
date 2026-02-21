#!/usr/bin/env python3
"""
Context Restoration Script - Run after Claude compaction

Regenerates key context sections:
1. Test status
2. Active tools/files
3. Dead code detection
4. Project metrics
5. Quick reference

Usage: python restore_context.py
"""

import json
import subprocess
from pathlib import Path
from datetime import datetime


def run_command(cmd, cwd=None):
    """Run shell command, return stdout."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=30,
        )
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return "[timeout]"
    except Exception as e:
        return f"[error: {e}]"


def analyze_tests(project_root):
    """Count and categorize tests."""
    test_count = run_command("find tests -name 'test_*.py' | wc -l", cwd=project_root)
    test_result = run_command("pytest --collect-only -q 2>/dev/null | tail -1", cwd=project_root)

    return {
        "test_files": test_count,
        "test_summary": test_result,
        "timestamp": datetime.now().isoformat(),
    }


def analyze_active_files(project_root):
    """List active (non-archive) files."""
    src_files = run_command("find src -type f -name '*.py' | wc -l", cwd=project_root)
    app_files = run_command("find app -type f -name '*.py' 2>/dev/null | wc -l", cwd=project_root)
    ui_files = run_command("find ui_textual -type f -name '*.py' 2>/dev/null | wc -l", cwd=project_root)

    return {
        "src_python_files": src_files,
        "app_python_files": app_files,
        "ui_python_files": ui_files,
    }


def find_dead_imports(project_root):
    """Run vulture for dead code detection."""
    result = run_command("vulture src/ app/ 2>/dev/null | head -10", cwd=project_root)
    return {
        "dead_code_samples": result or "[no vulture output]",
        "note": "Full audit: vulture src/ app/ --min-confidence 80",
    }


def calculate_metrics(project_root):
    """Calculate project health metrics."""
    lines_of_code = run_command("find src app -name '*.py' -exec wc -l {} + 2>/dev/null | tail -1", cwd=project_root)
    git_commits = run_command("git log --oneline | wc -l 2>/dev/null", cwd=project_root)
    git_size = run_command("du -sh .git 2>/dev/null | cut -f1", cwd=project_root)

    return {
        "lines_of_code": lines_of_code,
        "git_commits": git_commits,
        "git_size": git_size,
    }


def build_quick_reference(project_root, claude_md_path):
    """Extract quick reference from CLAUDE.md."""
    if not claude_md_path.exists():
        return {"note": "CLAUDE.md not found"}

    content = claude_md_path.read_text()

    # Extract Quick Start section
    if "## Quick Start" in content:
        start_idx = content.index("## Quick Start") + len("## Quick Start")
        end_idx = content.find("---", start_idx)
        quick_start = content[start_idx:end_idx].strip()[:200]
    else:
        quick_start = "[Quick Start not found in CLAUDE.md]"

    return {
        "quick_start_excerpt": quick_start,
        "claude_md_exists": True,
    }


def restore_context(project_root="."):
    """Main restoration function."""
    project_root = Path(project_root)

    print(f"🔄 Restoring context for {project_root.name}...")
    print()

    # 1. Test status
    print("✓ Analyzing tests...")
    tests = analyze_tests(project_root)
    print(f"  - Test files: {tests['test_files']}")
    print(f"  - Summary: {tests['test_summary']}")
    print()

    # 2. Active files
    print("✓ Scanning source files...")
    files = analyze_active_files(project_root)
    for key, value in files.items():
        print(f"  - {key}: {value}")
    print()

    # 3. Dead code
    print("✓ Checking for dead code (vulture)...")
    dead = find_dead_imports(project_root)
    if dead["dead_code_samples"] != "[no vulture output]":
        print(f"  {dead['dead_code_samples'][:100]}...")
    else:
        print("  [No dead code detected]")
    print()

    # 4. Metrics
    print("✓ Calculating project metrics...")
    metrics = calculate_metrics(project_root)
    for key, value in metrics.items():
        print(f"  - {key}: {value}")
    print()

    # 5. Quick reference
    print("✓ Reading CLAUDE.md...")
    ref = build_quick_reference(project_root, project_root / "CLAUDE.md")
    print(f"  - CLAUDE.md found: {ref.get('claude_md_exists', False)}")
    print()

    # Compile all context
    context = {
        "generated": datetime.now().isoformat(),
        "project": project_root.name,
        "tests": tests,
        "files": files,
        "dead_code": dead,
        "metrics": metrics,
        "quick_reference": ref,
    }

    # Output
    print("=" * 60)
    print("📊 CONTEXT RESTORED")
    print("=" * 60)
    print(json.dumps(context, indent=2))

    # Save to file
    output_file = project_root / ".claude" / "context_restore_output.json"
    output_file.parent.mkdir(exist_ok=True)
    output_file.write_text(json.dumps(context, indent=2))
    print(f"\n✅ Context saved to: {output_file}")

    return context


if __name__ == "__main__":
    import sys

    project = sys.argv[1] if len(sys.argv) > 1 else "."
    restore_context(project)
