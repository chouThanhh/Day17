from __future__ import annotations

from typing import Any

from .config import settings
from .context_budget import ContextBudgetManager
from .utils import cap_query, join_nonempty
from .zep_common import prime_eval_thread, render_graph_search


class StudentMemory:
    """Only this file needs to be edited by students."""

    def __init__(self, client: Any):
        self.client = client
        self.budget = ContextBudgetManager(settings.context_tokens)

    # NOTE: Zep rejects graph.search queries longer than 400 characters. Some
    # eval queries are longer than that, so wrap every query with
    # `cap_query(query)` (see src/utils.py) before passing it to graph.search.

    def retrieve_long_term(self, user_id: str, thread_id: str, query: str) -> str:
        # LAB TODO 1/4
        # The Context Block is built from the user graph, but Zep needs a fresh
        # thread slice holding the current query to decide what is relevant.
        prime_eval_thread(self.client, user_id, thread_id, query)

        user_context = self.client.thread.get_user_context(thread_id=thread_id)
        context_block = getattr(user_context, "context", "") or ""

        # Append user-scoped facts (edges) so validity ranges are visible for the
        # recency/conflict cases (E08). A generous limit keeps deadline and
        # open-loop facts from being cut off.
        fact_text = ""
        try:
            facts = self.client.graph.search(
                user_id=user_id,
                query=cap_query(query),
                scope="edges",
                limit=25,
            )
            fact_text = render_graph_search(facts)
        except Exception:
            fact_text = ""

        return join_nonempty([context_block, fact_text], sep="\n\n")

    def retrieve_episodic(self, user_id: str, query: str) -> str:
        # LAB TODO 2/4
        # Search the *user* graph (user_id, not graph_id) for raw episodes so the
        # trajectory + reflection markers survive. Cap each episode so a few
        # verbose session messages do not eat the whole episodic budget and hide
        # the concise reflection episodes.
        results = self.client.graph.search(
            user_id=user_id,
            query=cap_query(query),
            scope="episodes",
            limit=15,
        )
        return render_graph_search(results, episode_char_cap=180)

    def retrieve_semantic(self, graph_id: str, query: str) -> str:
        # LAB TODO 3/4
        # Standalone/shared graph: pass graph_id, never user_id. scope="episodes"
        # returns raw document text and keeps literal markers such as
        # PAYMENT-RULE-3 / CONN-POOL-FIRST; "auto" drops them. "nodes" is the
        # fallback for accounts where the episodes scope behaves differently.
        capped = cap_query(query)
        try:
            results = self.client.graph.search(
                graph_id=graph_id,
                query=capped,
                scope="episodes",
                limit=8,
            )
        except Exception:
            results = self.client.graph.search(
                graph_id=graph_id,
                query=capped,
                scope="nodes",
                limit=8,
            )
        return render_graph_search(results)

    def assemble_context(self, layers: dict[str, str]) -> tuple[str, dict[str, dict[str, int]]]:
        # LAB TODO 4/4
        # ContextBudgetManager already encodes the 10/4/3/3 teaching budget and
        # the short_term -> long_term -> episodic -> semantic priority order.
        return self.budget.assemble(layers)
