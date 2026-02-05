# executor.py
import subprocess
import tempfile
import os
import sys
import shutil
import re
from pathlib import Path
from typing import Tuple, List, Optional, Dict

def _resolve_playwright_command(tmp_path: str, headed: bool, project_root: Optional[Path] = None) -> Tuple[List[str], str]:
    """Resolve a runnable Playwright CLI invocation across Windows/Linux.

    Parameters:
        tmp_path: Path to spec file (absolute or relative to project_root).
        headed: Whether to append --headed.
        project_root: Root where Playwright config & node_modules live. Defaults to monorepo root.
    """
    # Add Node.js to PATH first so shutil.which can find it
    nodejs_path = r"C:\Program Files\nodejs"
    if nodejs_path not in os.environ.get("PATH", ""):
        os.environ["PATH"] = nodejs_path + os.pathsep + os.environ.get("PATH", "")
    
    project_root = project_root or Path(__file__).resolve().parents[2]
    cwd = str(project_root)

    # Playwright treats positional args as regex. On Windows, backslashes can break the match.
    # Normalize to forward slashes so the regex matches the file path reliably.
    arg_path = tmp_path.replace("\\", "/")
    # base_args = ["test", arg_path, "--reporter=line"]
    base_args = ["test", arg_path,]
    if headed:
        base_args.append("--headed")

    # Prefer local node_modules binaries first to avoid version conflicts
    bin_dir_win = project_root / "node_modules" / ".bin" / "playwright.cmd"
    bin_dir_unix = project_root / "node_modules" / ".bin" / "playwright"
    if bin_dir_win.exists():
        return [str(bin_dir_win), *base_args], cwd
    if bin_dir_unix.exists():
        return [str(bin_dir_unix), *base_args], cwd

    # Fallback to running the CLI JS directly
    cli_js = project_root / "node_modules" / "@playwright" / "test" / "cli.js"
    node_path = shutil.which("node") or shutil.which("node.exe")
    if node_path and cli_js.exists():
        return [node_path, str(cli_js), *base_args], cwd

    # Nothing found; craft helpful error
    raise FileNotFoundError(
        "Playwright CLI not found. Ensure Node and @playwright/test are installed (npm ci) "
        "and that npx is on PATH."
    )


def run_trial(script_content: str, headed: bool = True, env_overrides: Optional[Dict[str, str]] = None) -> Tuple[bool, str]:
    """Write script to a temp file and execute it via Playwright.

    Parameters:
      script_content: Combined TypeScript test content.
      headed: When True, pass --headed to Playwright for visible browser execution.

    Returns:
      (success, logs) where success is True if return code == 0.
    """
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".spec.ts") as tmp:
            tmp.write(script_content.encode("utf-8"))
            tmp_path = tmp.name

        cmd, cwd = _resolve_playwright_command(tmp_path, headed)

        # Merge environment with optional overrides (for trial-only creds)
        env = os.environ.copy()
        # Add Node.js to PATH for subprocess
        nodejs_path = r"C:\Program Files\nodejs"
        current_path = env.get("PATH", "")
        if nodejs_path not in current_path:
            env["PATH"] = nodejs_path + os.pathsep + current_path
            print(f"[Executor] Added Node.js to PATH: {nodejs_path}")
        if env_overrides:
            env.update(env_overrides)

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",  # avoid Windows codepage decode failures
            cwd=cwd,
            env=env,
        )

        stdout = result.stdout or ""
        stderr = result.stderr or ""
        # Determine if run was effectively skipped (no executed tests)
        only_skipped = False
        try:
            # Heuristic: summary contains "N skipped" and does not contain any "passed", "failed", or "flaky"
            has_skipped = bool(re.search(r"\b(\d+)\s+skipped\b", stdout))
            has_passed = bool(re.search(r"\b(\d+)\s+passed\b", stdout))
            has_failed = bool(re.search(r"\b(\d+)\s+failed\b", stdout))
            has_flaky = bool(re.search(r"\b(\d+)\s+flaky\b", stdout))
            only_skipped = has_skipped and not (has_passed or has_failed or has_flaky)
        except Exception:
            only_skipped = False

        success = (result.returncode == 0) and not only_skipped
        # Prepend the resolved command/cwd so callers can verify flags like --headed
        cmd_str = " ".join(cmd)
        header = f"$ {cmd_str}\n(cwd={cwd})\n"
        note = ("\n[notice] All tests were skipped; marking run as not executed.\n" if only_skipped else "")
        logs = header + stdout + "\n" + stderr + note
        try:
            os.unlink(tmp_path)  # cleanup temp file
        except OSError:
            pass
        return success, logs
    except Exception as e:  # pragma: no cover - defensive
        return False, f"Executor failure: {e}"


def _detect_test_dir(framework_root: Path) -> Path:
    """Attempt to detect Playwright testDir from playwright.config.*; fallback to ./tests.
    """
    config_candidates = [
        framework_root / 'playwright.config.ts',
        framework_root / 'playwright.config.js',
        framework_root / 'playwright.config.mjs',
        framework_root / 'playwright.config.cjs',
    ]
    for cfg in config_candidates:
        if not cfg.exists():
            continue
        try:
            text = cfg.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            continue
        m = re.search(r'testDir\s*:\s*["\']([^"\']+)["\']', text)
        if m:
            candidate = framework_root / m.group(1)
            return candidate
    return framework_root / 'tests'


def run_trial_in_framework(script_content: str, framework_root: Path, headed: bool = True, env_overrides: Optional[Dict[str, str]] = None) -> Tuple[bool, str]:
    """Persist a temporary spec INSIDE the framework repo (under detected testDir) so Playwright config matches.

    This avoids 'No tests found' when testDir excludes system temp locations.
    """
    try:
        # Apply trial adapter transformations BEFORE writing to file
        try:
            # Ensure parent directory is in sys.path for import
            parent_dir = str(Path(__file__).resolve().parent.parent)
            if parent_dir not in sys.path:
                sys.path.insert(0, parent_dir)
            from app.trial_spec_adapter import adapt_spec_content_for_trial
            print(f"[Executor] Applying trial adapter to script (length: {len(script_content)})")
            script_content, adapted = adapt_spec_content_for_trial(script_content, framework_root)
            print(f"[Executor] Trial adapter result: adapted={adapted}, new length={len(script_content)}")
        except Exception as e:
            print(f"[Executor] Trial adapter failed: {e}")
            import traceback
            traceback.print_exc()
        
        test_dir = _detect_test_dir(framework_root)
        test_dir.mkdir(parents=True, exist_ok=True)
        
        # Debug: Save modified script to verify injection
        debug_path = test_dir / '_last_trial_script.ts'
        try:
            debug_path.write_text(script_content, encoding='utf-8')
            print(f"[Executor] Debug script saved to: {debug_path}")
        except Exception:
            pass
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.spec.ts', dir=str(test_dir)) as tmp:
            tmp.write(script_content.encode('utf-8'))
            tmp_path = tmp.name
        # Use relative path from framework_root so Playwright's regex matches within testDir.
        try:
            rel_to_root = Path(tmp_path).relative_to(framework_root)
            spec_arg = rel_to_root.as_posix()
        except ValueError:
            spec_arg = tmp_path.replace('\\', '/')
        cmd, cwd = _resolve_playwright_command(spec_arg, headed, project_root=framework_root)
        env = os.environ.copy()
        # Add Node.js to PATH for subprocess
        nodejs_path = r"C:\Program Files\nodejs"
        current_path = env.get("PATH", "")
        if nodejs_path not in current_path:
            env["PATH"] = nodejs_path + os.pathsep + current_path
            print(f"[Executor] Added Node.js to PATH: {nodejs_path}")
        if env_overrides:
            env.update(env_overrides)

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            cwd=str(framework_root),
            env=env,
        )
        stdout = result.stdout or ''
        stderr = result.stderr or ''
        only_skipped = False
        try:
            has_skipped = bool(re.search(r"\b(\d+)\s+skipped\b", stdout))
            has_passed = bool(re.search(r"\b(\d+)\s+passed\b", stdout))
            has_failed = bool(re.search(r"\b(\d+)\s+failed\b", stdout))
            has_flaky = bool(re.search(r"\b(\d+)\s+flaky\b", stdout))
            only_skipped = has_skipped and not (has_passed or has_failed or has_flaky)
        except Exception:
            only_skipped = False
        success = (result.returncode == 0) and not only_skipped
        cmd_str = ' '.join(cmd)
        header = f"$ {cmd_str}\n(cwd={framework_root})\n"
        note = ("\n[notice] All tests were skipped; marking run as not executed.\n" if only_skipped else '')
        logs = header + stdout + '\n' + stderr + note
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        return success, logs
    except Exception as e:  # pragma: no cover
        return False, f'Framework trial failure: {e}'
