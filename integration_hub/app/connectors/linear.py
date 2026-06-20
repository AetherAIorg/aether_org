from __future__ import annotations

import hashlib
import hmac
import logging
from typing import Any

import httpx

from app.agent.context_agent import ContextAgent
from app.query_router import parse_query as shared_parse_query

logger = logging.getLogger(__name__)

LINEAR_GRAPHQL_URL = "https://api.linear.app/graphql"

_ISSUE_CREATE = """
mutation IssueCreate($input: IssueCreateInput!) {
  issueCreate(input: $input) {
    success
    issue { id identifier url }
  }
}
"""

_COMMENT_CREATE = """
mutation CommentCreate($input: CommentCreateInput!) {
  commentCreate(input: $input) {
    success
    comment { id }
  }
}
"""


class LinearConnector:
    name = "linear"

    def __init__(
        self,
        api_key: str,
        webhook_secret: str,
        team_id: str,
        bot_user_id: str = "",
        mention_token: str = "@MetricGraph",
        extra_mention_tokens: list[str] | None = None,
    ) -> None:
        self.api_key = api_key
        self.webhook_secret = webhook_secret
        self.team_id = team_id
        self.bot_user_id = bot_user_id
        self.mention_token = mention_token
        self.mention_tokens = [mention_token, "@Margin"] + (extra_mention_tokens or [])
        self._client = httpx.Client(timeout=20.0)

    def enabled(self) -> bool:
        return bool(self.api_key)

    def notify(self, event: Event) -> None:
        # Outbound notifications for Linear are handled by the router (issue
        # creation with dedupe). Nothing to do for the generic notify path.
        return

    # --- GraphQL helpers ---

    def _graphql(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        resp = self._client.post(
            LINEAR_GRAPHQL_URL,
            headers={"Authorization": self.api_key, "Content-Type": "application/json"},
            json={"query": query, "variables": variables},
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("errors"):
            raise RuntimeError(f"Linear GraphQL error: {data['errors']}")
        return data["data"]

    def create_issue(self, title: str, description: str) -> dict[str, Any] | None:
        if not self.enabled() or not self.team_id:
            logger.info("Linear disabled or no team id; would create issue: %s", title)
            return None
        data = self._graphql(
            _ISSUE_CREATE,
            {"input": {"teamId": self.team_id, "title": title, "description": description}},
        )
        result = data.get("issueCreate", {})
        if not result.get("success"):
            logger.warning("Linear issueCreate did not succeed for %s", title)
            return None
        return result.get("issue")

    def create_comment(self, issue_id: str, body: str, parent_id: str | None = None) -> bool:
        if not self.enabled():
            logger.info("Linear disabled; would comment on %s: %s", issue_id, body[:80])
            return False
        payload: dict[str, Any] = {"issueId": issue_id, "body": body}
        if parent_id:
            payload["parentId"] = parent_id
        data = self._graphql(_COMMENT_CREATE, {"input": payload})
        return bool(data.get("commentCreate", {}).get("success"))

    # --- Inbound webhook handling ---

    def verify_signature(self, signature: str, raw_body: bytes) -> bool:
        if not self.webhook_secret or not signature:
            return False
        digest = hmac.new(
            self.webhook_secret.encode("utf-8"), raw_body, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(digest, signature)

    def extract_comment(self, body: dict[str, Any]) -> dict[str, Any] | None:
        """Pull the relevant fields from a Linear Comment webhook payload."""
        if body.get("type") != "Comment" or body.get("action") != "create":
            return None
        data = body.get("data") or {}
        issue = data.get("issue") or {}
        return {
            "comment_id": data.get("id"),
            "text": data.get("body", "") or "",
            "issue_id": data.get("issueId") or issue.get("id"),
            "parent_id": data.get("parentId"),
            "author_id": data.get("userId") or (data.get("user") or {}).get("id"),
        }

    def parse_query(self, text: str) -> tuple[str, str] | None:
        return shared_parse_query(text, self.mention_tokens)

    def answer_query(self, agent: ContextAgent, intent: str, query: str) -> str:
        """Build a Linear-comment markdown answer via ContextAgent."""
        return agent.answer(intent, query)

    def close(self) -> None:
        self._client.close()
