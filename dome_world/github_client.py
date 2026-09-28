"""
Dome-World GitHub Landing Board Client

Lightweight wrapper around the GitHub REST API (via `requests`) for
posting formatted Markdown observations to a target repository issue
or discussion — "The Landing Board".

Passive architectural stance:
- This client is a pure *publisher*. It never reads swarm state back
  into the local system as control input.
- Failures are logged and surfaced; they do not halt the local
  telemetry pipeline. The Landing Board is an observation sink, not
  a dependency for continued swarm operation.
- Authentication is token-based and expected to be supplied via
  environment variable or explicit argument — never hard-coded.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

import requests

from .models import Observation

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"


class GitHubLandingBoard:
    """
    Posts Observation objects to a GitHub Issue that serves as
    The Landing Board.

    Typical usage:
        board = GitHubLandingBoard(
            owner="your-org",
            repo="dome-world",
            issue_number=1,          # the dedicated Landing Board issue
            token=os.getenv("GITHUB_TOKEN"),
        )
        board.post_observation(obs)
    """

    def __init__(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        token: Optional[str] = None,
        api_base: str = GITHUB_API,
    ):
        self.owner = owner
        self.repo = repo
        self.issue_number = issue_number
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.api_base = api_base.rstrip("/")
        self.session = requests.Session()
        if self.token:
            self.session.headers.update({
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            })
        else:
            logger.warning(
                "No GitHub token supplied. Authenticated requests will fail. "
                "Set GITHUB_TOKEN or pass token= explicitly."
            )

    @property
    def issue_url(self) -> str:
        return f"{self.api_base}/repos/{self.owner}/{self.repo}/issues/{self.issue_number}/comments"

    def post_observation(self, observation: Observation, dry_run: bool = False) -> Dict[str, Any]:
        """
        Publish an Observation as a new comment on the Landing Board issue.

        Args:
            observation: Fully rendered Observation (title is used as a
                         header inside the comment body).
            dry_run:     If True, log the payload and return a mock
                         response without contacting GitHub. Ideal for
                         local testing and CI.

        Returns:
            The GitHub API response JSON (or a mock dict in dry-run mode).
        """
        # Compose the comment body. We embed the title so the Landing
        # Board remains readable even when comments are collapsed.
        body = (
            f"## {observation.title}\n\n"
            f"{observation.body_markdown}\n\n"
            f"_Tags: {', '.join(f'`{t}`' for t in observation.tags)}_\n"
        )

        payload = {"body": body}

        if dry_run:
            logger.info("[DRY-RUN] Would post to %s", self.issue_url)
            logger.debug("Payload:\n%s", body)
            return {
                "dry_run": True,
                "url": self.issue_url,
                "body_preview": body[:200] + ("..." if len(body) > 200 else ""),
            }

        if not self.token:
            raise RuntimeError(
                "Cannot post: no GitHub token available. "
                "Set GITHUB_TOKEN environment variable or pass token=."
            )

        logger.info("Posting observation to Landing Board issue #%s ...", self.issue_number)
        resp = self.session.post(self.issue_url, json=payload, timeout=30)

        if resp.status_code == 201:
            data = resp.json()
            logger.info("Posted successfully → %s", data.get("html_url", "unknown"))
            return data

        # Surface the error clearly; never swallow it.
        logger.error(
            "GitHub API error %s: %s",
            resp.status_code,
            resp.text[:500],
        )
        resp.raise_for_status()
        return {}  # unreachable, but keeps type checkers happy

    def health_check(self) -> bool:
        """
        Lightweight connectivity / auth test against the target issue.
        Returns True if the issue is reachable with the current token.
        """
        url = f"{self.api_base}/repos/{self.owner}/{self.repo}/issues/{self.issue_number}"
        try:
            resp = self.session.get(url, timeout=10)
            return resp.status_code == 200
        except requests.RequestException as exc:
            logger.warning("Health check failed: %s", exc)
            return False
