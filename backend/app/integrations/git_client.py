"""Git clone/pull operations for ETL code repository."""

import logging
import os
import subprocess
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)


class GitClient:
    def __init__(self):
        self.repo_url = settings.git_repo_url
        self.clone_path = Path(settings.git_clone_path)
        self.branch = settings.git_branch
        self.https_token = settings.git_https_token
        self._connected = False

    def _get_env(self) -> dict[str, str]:
        env = os.environ.copy()
        if self.https_token:
            # Use token for HTTPS auth via credential helper
            env["GIT_ASKPASS"] = "echo"
            env["GIT_TERMINAL_PROMPT"] = "0"
        return env

    def _get_clone_url(self) -> str:
        """Build the clone URL, embedding HTTPS token if configured."""
        repo_url = str(self.repo_url)

        # Local path (dev environment)
        if repo_url.startswith("/"):
            return f"file://{repo_url}"

        # Embed token into HTTPS URL: https://token@github.com/org/repo.git
        if self.https_token and repo_url.startswith("https://"):
            return repo_url.replace("https://", f"https://{self.https_token}@", 1)

        return repo_url

    def _run(self, cmd: list[str], cwd: str | None = None) -> subprocess.CompletedProcess:
        return subprocess.run(
            cmd,
            cwd=cwd,
            env=self._get_env(),
            capture_output=True,
            text=True,
            timeout=120,
        )

    @property
    def is_connected(self) -> bool:
        return self._connected

    def clone_or_pull(self) -> bool:
        """Clone the repo if it doesn't exist, otherwise pull latest changes."""
        try:
            if self.clone_path.exists() and (self.clone_path / ".git").exists():
                return self._pull()
            return self._clone()
        except Exception as e:
            logger.exception("Git operation failed: %s", e)
            self._connected = False
            return False

    def _clone(self) -> bool:
        self.clone_path.mkdir(parents=True, exist_ok=True)

        # If the directory has contents (e.g. Docker volume), clean it first
        for item in self.clone_path.iterdir():
            import shutil
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()

        clone_url = self._get_clone_url()
        is_local = str(self.repo_url).startswith("/")

        cmd = ["git", "clone", "--branch", self.branch]
        if not is_local:
            cmd += ["--single-branch", "--depth", "1"]
        cmd += [clone_url, str(self.clone_path)]

        result = self._run(cmd)
        if result.returncode == 0:
            logger.info("Git clone successful: %s", self.repo_url)
            self._connected = True
            return True
        logger.error("Git clone failed: %s", result.stderr)
        self._connected = False
        return False

    def _pull(self) -> bool:
        result = self._run(
            ["git", "pull", "origin", self.branch],
            cwd=str(self.clone_path),
        )
        if result.returncode == 0:
            logger.info("Git pull successful")
            self._connected = True
            return True
        logger.error("Git pull failed: %s", result.stderr)
        # Still consider connected if we have a valid clone
        self._connected = (self.clone_path / ".git").exists()
        return False

    def get_dagger_path(self) -> Path:
        """Return the path to the dagger folder in the cloned repo."""
        return self.clone_path / "dagger"

    def has_repo(self) -> bool:
        """Check if we have a cloned repo available."""
        return self.clone_path.exists() and (self.clone_path / ".git").exists()


git_client = GitClient()
