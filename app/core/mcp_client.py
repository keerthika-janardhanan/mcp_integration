"""MCP client utilities for integrating Model Context Protocol servers."""

from __future__ import annotations

import os
import json
import subprocess
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)

class MCPClient:
    """Base class for interacting with MCP servers."""
    
    def __init__(self, server_name: str):
        self.server_name = server_name
        self.mcp_config = self._load_mcp_config()
        
    def _load_mcp_config(self) -> Dict[str, Any]:
        """Load MCP configuration from .vscode/mcp.json."""
        config_path = Path(__file__).parent.parent.parent / ".vscode" / "mcp.json"
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = json.load(f)
                return config.get('servers', {}).get(self.server_name, {})
        return {}
    
    def is_configured(self) -> bool:
        """Check if the MCP server is configured."""
        return bool(self.mcp_config)


class MicrosoftDocsMCP(MCPClient):
    """Client for Microsoft Docs MCP server."""
    
    def __init__(self):
        super().__init__("microsoft-docs")
        
    def search_docs(self, query: str, max_results: int = 10) -> List[Dict[str, str]]:
        """Search Microsoft documentation.
        
        Args:
            query: Search query for Microsoft docs
            max_results: Maximum number of results to return
            
        Returns:
            List of dictionaries with 'title', 'url', and 'content' keys
        """
        if not self.is_configured():
            logger.warning("Microsoft Docs MCP not configured, returning empty results")
            return []
            
        try:
            # In production, this would call the actual MCP server
            # For now, return placeholder that indicates the integration point
            logger.info(f"[MicrosoftDocsMCP] Searching for: {query}")
            return [{
                "title": f"Playwright Best Practices for {query}",
                "url": "https://playwright.dev/docs/best-practices",
                "content": "Use getByRole, getByLabel, and getByText for resilient selectors. Avoid XPath when possible."
            }]
        except Exception as e:
            logger.error(f"Microsoft Docs MCP search failed: {e}")
            return []
    
    def search_code_samples(self, query: str, language: Optional[str] = None, max_results: int = 20) -> List[Dict[str, str]]:
        """Search for code samples in Microsoft documentation.
        
        Args:
            query: Search query for code samples
            language: Programming language filter (typescript, python, etc.)
            max_results: Maximum number of results to return
            
        Returns:
            List of dictionaries with code samples
        """
        if not self.is_configured():
            logger.warning("Microsoft Docs MCP not configured, returning empty results")
            return []
            
        try:
            logger.info(f"[MicrosoftDocsMCP] Searching code samples: {query} (lang: {language})")
            # Integration point for actual MCP call
            return [{
                "code": "await page.getByRole('button', { name: 'Submit' }).click();",
                "language": language or "typescript",
                "source": "https://playwright.dev/docs/locators"
            }]
        except Exception as e:
            logger.error(f"Microsoft Docs code sample search failed: {e}")
            return []
    
    def fetch_doc_page(self, url: str) -> Optional[str]:
        """Fetch complete documentation page content.
        
        Args:
            url: URL of the Microsoft documentation page
            
        Returns:
            Markdown content of the page
        """
        if not self.is_configured():
            logger.warning("Microsoft Docs MCP not configured")
            return None
            
        try:
            logger.info(f"[MicrosoftDocsMCP] Fetching doc page: {url}")
            # Integration point for actual MCP call
            return "# Playwright Documentation\n\nContent would be fetched here..."
        except Exception as e:
            logger.error(f"Microsoft Docs page fetch failed: {e}")
            return None


class GitHubMCP(MCPClient):
    """Client for GitHub MCP server."""
    
    def __init__(self):
        super().__init__("github")
        
    def search_repositories(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search GitHub repositories.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            
        Returns:
            List of repository information
        """
        if not self.is_configured():
            logger.warning("GitHub MCP not configured, returning empty results")
            return []
            
        try:
            logger.info(f"[GitHubMCP] Searching repositories: {query}")
            # Integration point for actual MCP call
            return []
        except Exception as e:
            logger.error(f"GitHub MCP repository search failed: {e}")
            return []
    
    def search_code(self, query: str, repo: Optional[str] = None, max_results: int = 20) -> List[Dict[str, str]]:
        """Search for code in GitHub repositories.
        
        Args:
            query: Code search query
            repo: Optional repository to search in (format: owner/repo)
            max_results: Maximum number of results
            
        Returns:
            List of code snippets with metadata
        """
        if not self.is_configured():
            logger.warning("GitHub MCP not configured, returning empty results")
            return []
            
        try:
            logger.info(f"[GitHubMCP] Searching code: {query} in {repo or 'all repos'}")
            # Integration point for actual MCP call
            return []
        except Exception as e:
            logger.error(f"GitHub MCP code search failed: {e}")
            return []
    
    def clone_repository(self, repo_url: str, target_path: Path, branch: Optional[str] = None) -> bool:
        """Clone a GitHub repository using git.
        
        Args:
            repo_url: Repository URL
            target_path: Local path to clone to
            branch: Optional branch to clone
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"[GitHubMCP] Cloning {repo_url} to {target_path}")
            
            cmd = ["git", "clone"]
            if branch:
                cmd.extend(["--branch", branch])
            cmd.extend([repo_url, str(target_path)])
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                logger.info(f"[GitHubMCP] Successfully cloned {repo_url}")
                return True
            else:
                logger.error(f"[GitHubMCP] Clone failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"[GitHubMCP] Clone error: {e}")
            return False


class FilesystemMCP(MCPClient):
    """Client for Filesystem MCP server."""
    
    def __init__(self):
        super().__init__("filesystem")
        
    def list_directory(self, path: Path) -> List[str]:
        """List contents of a directory.
        
        Args:
            path: Directory path
            
        Returns:
            List of file/directory names
        """
        if not self.is_configured():
            logger.warning("Filesystem MCP not configured, using direct filesystem access")
            if path.exists():
                return [str(p.name) for p in path.iterdir()]
            return []
            
        try:
            logger.info(f"[FilesystemMCP] Listing directory: {path}")
            # Integration point for actual MCP call
            if path.exists():
                return [str(p.name) for p in path.iterdir()]
            return []
        except Exception as e:
            logger.error(f"Filesystem MCP list directory failed: {e}")
            return []
    
    def create_directory(self, path: Path, parents: bool = True) -> bool:
        """Create a directory.
        
        Args:
            path: Directory path to create
            parents: Create parent directories if needed
            
        Returns:
            True if successful
        """
        try:
            logger.info(f"[FilesystemMCP] Creating directory: {path}")
            path.mkdir(parents=parents, exist_ok=True)
            return True
        except Exception as e:
            logger.error(f"Filesystem MCP create directory failed: {e}")
            return False
    
    def safe_write_file(self, path: Path, content: str, backup: bool = True) -> bool:
        """Safely write content to a file with optional backup.
        
        Args:
            path: File path
            content: Content to write
            backup: Create backup if file exists
            
        Returns:
            True if successful
        """
        try:
            if backup and path.exists():
                backup_path = path.with_suffix(path.suffix + '.backup')
                import shutil
                shutil.copy2(path, backup_path)
                logger.info(f"[FilesystemMCP] Created backup: {backup_path}")
            
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding='utf-8')
            logger.info(f"[FilesystemMCP] Wrote file: {path}")
            return True
            
        except Exception as e:
            logger.error(f"Filesystem MCP write file failed: {e}")
            return False


# Singleton instances
_microsoft_docs_mcp: Optional[MicrosoftDocsMCP] = None
_github_mcp: Optional[GitHubMCP] = None
_filesystem_mcp: Optional[FilesystemMCP] = None


def get_microsoft_docs_mcp() -> MicrosoftDocsMCP:
    """Get or create Microsoft Docs MCP client singleton."""
    global _microsoft_docs_mcp
    if _microsoft_docs_mcp is None:
        _microsoft_docs_mcp = MicrosoftDocsMCP()
    return _microsoft_docs_mcp


def get_github_mcp() -> GitHubMCP:
    """Get or create GitHub MCP client singleton."""
    global _github_mcp
    if _github_mcp is None:
        _github_mcp = GitHubMCP()
    return _github_mcp


def get_filesystem_mcp() -> FilesystemMCP:
    """Get or create Filesystem MCP client singleton."""
    global _filesystem_mcp
    if _filesystem_mcp is None:
        _filesystem_mcp = FilesystemMCP()
    return _filesystem_mcp
