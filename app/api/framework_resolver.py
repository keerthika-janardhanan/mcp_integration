from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Tuple
import hashlib
import subprocess
import re
import logging

try:
    from ..core.mcp_client import get_github_mcp, get_filesystem_mcp
except ImportError:
    # Fallback for direct script execution
    from app.core.mcp_client import get_github_mcp, get_filesystem_mcp

logger = logging.getLogger(__name__)

# Track which repositories have already been pulled this session
_PULLED_REPOS: set[str] = set()


def reset_pull_cache(repo_path: Optional[str] = None) -> None:
    """Reset the pull cache. If repo_path provided, reset only that repo; otherwise reset all.
    
    Call this when user explicitly updates repository details to force a fresh pull.
    """
    global _PULLED_REPOS
    if repo_path:
        _PULLED_REPOS.discard(str(Path(repo_path).resolve()))
        print(f"[FrameworkResolver] Pull cache reset for {repo_path}")
    else:
        _PULLED_REPOS.clear()
        print(f"[FrameworkResolver] Pull cache cleared for all repositories")


def _normalize_remote_repo_input(raw: str) -> Tuple[str, Optional[str]]:
    cleaned = raw.replace("\\", "/").strip()
    cleaned = cleaned.replace("https:/", "https://").replace("http:/", "http://")
    branch_in_url = None
    if cleaned.startswith("git@"):
        return cleaned, branch_in_url
    if "://" not in cleaned and cleaned.startswith("github.com"):
        cleaned = f"https://{cleaned}"
    if cleaned.startswith("http") and "/tree/" in cleaned:
        base, remainder = cleaned.split("/tree/", 1)
        branch_in_url = remainder.split("/", 1)[0]
        cleaned = base
    if cleaned.endswith("/"):
        cleaned = cleaned[:-1]
    if cleaned.startswith("http") and not cleaned.endswith(".git"):
        cleaned = f"{cleaned}.git"
    return cleaned, branch_in_url


def _create_default_framework_structure(base_path: Path) -> Path:
    """Create a default Playwright TypeScript framework structure for fresh starts."""
    default_framework = base_path / "default-playwright-framework"
    
    if default_framework.exists():
        return default_framework
    
    # Create directory structure
    default_framework.mkdir(parents=True, exist_ok=True)
    (default_framework / "tests").mkdir(exist_ok=True)
    (default_framework / "pages").mkdir(exist_ok=True)
    (default_framework / "locators").mkdir(exist_ok=True)
    
    # Create package.json
    package_json = default_framework / "package.json"
    package_json.write_text('''{
  "name": "default-playwright-framework",
  "version": "1.0.0",
  "description": "Auto-generated Playwright TypeScript test framework",
  "scripts": {
    "test": "playwright test",
    "test:headed": "playwright test --headed",
    "test:debug": "playwright test --debug"
  },
  "devDependencies": {
    "@playwright/test": "^1.40.0",
    "@types/node": "^20.10.0",
    "typescript": "^5.3.0"
  }
}
''')
    
    # Create playwright.config.ts
    playwright_config = default_framework / "playwright.config.ts"
    playwright_config.write_text('''import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    baseURL: process.env.BASE_URL || 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
''')
    
    # Create tsconfig.json
    tsconfig = default_framework / "tsconfig.json"
    tsconfig.write_text('''{
  "compilerOptions": {
    "target": "ES2022",
    "module": "commonjs",
    "moduleResolution": "node",
    "esModuleInterop": true,
    "skipLibCheck": true,
    "strict": true,
    "resolveJsonModule": true,
    "types": ["node", "@playwright/test"]
  },
  "include": ["**/*.ts"],
  "exclude": ["node_modules"]
}
''')
    
    # Create README
    readme = default_framework / "README.md"
    readme.write_text('''# Default Playwright Framework

This is an auto-generated Playwright TypeScript test framework.

## Setup

```bash
npm install
npx playwright install
```

## Run Tests

```bash
npm test
```

## Structure

- `tests/` - Test specification files
- `pages/` - Page Object Model classes
- `locators/` - Locator definitions and utilities
''')
    
    # Create .gitignore
    gitignore = default_framework / ".gitignore"
    gitignore.write_text('''node_modules/
test-results/
playwright-report/
playwright/.cache/
.env
''')
    
    return default_framework


def resolve_framework_root(explicit: Optional[str] = None) -> Path:
    """Resolve the framework repository root path.

    Extended behavior: if an explicit value resembles a remote git URL, clone (once) into ./framework_repos/<hash>.
    Order:
      1) Explicit local path or remote URL (auto-clone)
      2) ENV FRAMEWORK_REPO_ROOT if exists
      3) First directory under ./framework_repos
    """
    # Allow override to keep consistency across all endpoints
    clone_base_env = os.getenv("FRAMEWORK_CLONE_BASE", "framework_repos")
    default_root = Path(clone_base_env).expanduser().resolve()
    default_root.mkdir(parents=True, exist_ok=True)

    # 1) Explicit handling
    def _extract_embedded_remote(raw: str) -> Optional[str]:
        r"""Extract a remote git URL if the user accidentally prefixed it with a local path.
        Example: C:\workspace\git@github.com:org/repo.git -> git@github.com:org/repo.git
        """
        markers = ["git@github.com:", "https://github.com/", "http://github.com/"]
        for marker in markers:
            idx = raw.find(marker)
            if idx != -1:
                return raw[idx:].replace("\\", "/").strip()
        return None

    if explicit:
        raw = explicit.strip()
        # Detect embedded remote even if user passed a combined local+remote path
        embedded = _extract_embedded_remote(raw)
        if embedded:
            raw = embedded
        is_remote = bool(re.match(r"^(git@|https?://).*", raw)) or ("github.com" in raw and (raw.startswith("git@") or "https://" in raw or "http://" in raw))
        if is_remote:
            clone_url, branch_in_url = _normalize_remote_repo_input(raw)
            # Canonicalize clone_url to reduce duplicate hashes
            base_canonical = clone_url.rstrip('/')
            if base_canonical.endswith('.git.git'):
                base_canonical = base_canonical[:-4]
            # Remove /tree/<branch> from hash source if present (already extracted)
            base_canonical = re.sub(r'/tree/[^/]+$', '', base_canonical)
            slug_source = base_canonical + (f"#{branch_in_url}" if branch_in_url else "")
            local_slug = hashlib.sha1(slug_source.encode("utf-8")).hexdigest()[:12]
            target_dir = (default_root / local_slug).resolve()
            if not target_dir.exists():
                target_dir.parent.mkdir(parents=True, exist_ok=True)
                try:
                    # Use GitHub MCP for better cloning
                    github_mcp = get_github_mcp()
                    logger.info(f"[FrameworkResolver] Cloning repository from {clone_url} using GitHub MCP...")
                    
                    # Try GitHub MCP clone first, fallback to direct git
                    success = github_mcp.clone_repository(clone_url, target_dir, branch=branch_in_url)
                    
                    if not success:
                        # Fallback to direct git clone
                        logger.info(f"[FrameworkResolver] MCP clone unavailable, using direct git clone...")
                        cmd = ["git", "clone"]
                        if branch_in_url:
                            cmd.extend(["--branch", branch_in_url])
                        cmd.extend([clone_url, str(target_dir)])
                        subprocess.run(cmd, check=True, capture_output=True)
                    
                    # Use Filesystem MCP to verify structure
                    filesystem_mcp = get_filesystem_mcp()
                    contents = filesystem_mcp.list_directory(target_dir)
                    logger.info(f"[FrameworkResolver] Cloned repository contains: {', '.join(contents[:10])}")
                    logger.info(f"[FrameworkResolver] Successfully cloned repository to {target_dir}")
                    
                    # Install dependencies if package.json exists
                    package_json = target_dir / "package.json"
                    if package_json.exists():
                        logger.info(f"[FrameworkResolver] Installing dependencies with npm ci...")
                        try:
                            # Ensure Node.js is in PATH
                            nodejs_path = r"C:\Program Files\nodejs"
                            env = os.environ.copy()
                            if nodejs_path not in env.get("PATH", ""):
                                env["PATH"] = nodejs_path + os.pathsep + env.get("PATH", "")
                            
                            result = subprocess.run(
                                ["npm", "ci"],
                                cwd=str(target_dir),
                                capture_output=True,
                                text=True,
                                env=env,
                                timeout=300  # 5 minute timeout
                            )
                            if result.returncode == 0:
                                logger.info(f"[FrameworkResolver] ✓ Dependencies installed successfully")
                            else:
                                logger.warning(f"[FrameworkResolver] npm ci failed: {result.stderr}")
                                # Try npm install as fallback
                                logger.info(f"[FrameworkResolver] Trying npm install as fallback...")
                                result = subprocess.run(
                                    ["npm", "install"],
                                    cwd=str(target_dir),
                                    capture_output=True,
                                    text=True,
                                    env=env,
                                    timeout=300
                                )
                                if result.returncode == 0:
                                    logger.info(f"[FrameworkResolver] ✓ Dependencies installed via npm install")
                                else:
                                    logger.error(f"[FrameworkResolver] npm install also failed: {result.stderr}")
                        except subprocess.TimeoutExpired:
                            logger.error(f"[FrameworkResolver] npm ci timed out after 5 minutes")
                        except FileNotFoundError:
                            logger.error(f"[FrameworkResolver] npm not found in PATH. Ensure Node.js is installed.")
                        except Exception as e:
                            logger.error(f"[FrameworkResolver] Dependency installation failed: {e}")
                    
                except (subprocess.CalledProcessError, FileNotFoundError) as exc:
                    raise FileNotFoundError(f"Git clone failed for '{clone_url}': {exc}") from exc
            else:
                # Repository already exists - only pull once per session when first accessed
                # After that, work with local modifications under framework_repos/
                print(f"[FrameworkResolver] Repository already exists at {target_dir}")
                
                repo_key = str(target_dir)
                
                if repo_key not in _PULLED_REPOS:
                    # First time accessing this repo in current session - pull latest
                    try:
                        print(f"[FrameworkResolver] First access - pulling latest changes from remote...")
                        subprocess.run(["git", "-C", str(target_dir), "fetch", "--all"], check=True, capture_output=True)
                        # Try to pull, but don't fail if there are local changes
                        result = subprocess.run(
                            ["git", "-C", str(target_dir), "pull"],
                            capture_output=True,
                            text=True
                        )
                        if result.returncode == 0:
                            print(f"[FrameworkResolver] Successfully pulled latest changes")
                        else:
                            print(f"[FrameworkResolver] Pull skipped or failed: {result.stderr.strip()}")
                            print(f"[FrameworkResolver] Using existing local version (may include uncommitted changes)")
                        
                        # Mark this repo as pulled for this session
                        _PULLED_REPOS.add(repo_key)
                    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
                        print(f"[FrameworkResolver] Git operations unavailable: {exc}")
                        print(f"[FrameworkResolver] Using existing local version")
                        # Still mark as "pulled" to avoid repeated failures
                        _PULLED_REPOS.add(repo_key)
                else:
                    print(f"[FrameworkResolver] Using local repository (already synced this session)")
                
                # Always check and install dependencies if node_modules is missing
                node_modules = target_dir / "node_modules"
                package_json = target_dir / "package.json"
                if package_json.exists() and not node_modules.exists():
                    logger.info(f"[FrameworkResolver] node_modules missing, installing dependencies...")
                    try:
                        # Ensure Node.js is in PATH
                        nodejs_path = r"C:\Program Files\nodejs"
                        env = os.environ.copy()
                        if nodejs_path not in env.get("PATH", ""):
                            env["PATH"] = nodejs_path + os.pathsep + env.get("PATH", "")
                        
                        result = subprocess.run(
                            ["npm", "ci"],
                            cwd=str(target_dir),
                            capture_output=True,
                            text=True,
                            env=env,
                            timeout=300
                        )
                        if result.returncode == 0:
                            logger.info(f"[FrameworkResolver] ✓ Dependencies installed successfully")
                        else:
                            logger.warning(f"[FrameworkResolver] npm ci failed, trying npm install...")
                            result = subprocess.run(
                                ["npm", "install"],
                                cwd=str(target_dir),
                                capture_output=True,
                                text=True,
                                env=env,
                                timeout=300
                            )
                            if result.returncode == 0:
                                logger.info(f"[FrameworkResolver] ✓ Dependencies installed via npm install")
                    except Exception as e:
                        logger.error(f"[FrameworkResolver] Failed to install dependencies: {e}")
            
            if branch_in_url:
                try:
                    subprocess.run(["git", "-C", str(target_dir), "checkout", branch_in_url], check=True)
                except (subprocess.CalledProcessError, FileNotFoundError) as exc:
                    raise FileNotFoundError(f"Git checkout failed for branch '{branch_in_url}': {exc}") from exc
            return target_dir
        else:
            local_path = Path(raw).expanduser().resolve()
            if local_path.exists() and local_path.is_dir():
                return local_path
            # Fall through to other strategies if explicit path not found

    # 2) Environment variable
    env_root = os.getenv("FRAMEWORK_REPO_ROOT")
    if env_root:
        env_path = Path(env_root).expanduser().resolve()
        if env_path.exists() and env_path.is_dir():
            return env_path

    # 3) First directory under framework_repos
    subdirs = [p for p in default_root.iterdir() if p.is_dir()]
    subdirs.sort(key=lambda p: p.name)
    if subdirs:
        return subdirs[0]

    # 4) No framework found - create default structure
    print("[FrameworkResolver] No framework repository found. Creating default Playwright framework...")
    return _create_default_framework_structure(default_root)
