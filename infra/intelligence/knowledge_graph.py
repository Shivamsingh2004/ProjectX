"""
Knowledge Graph: Relationship Intelligence Layer.

Models the social graph between users, platforms, conversations, and
AI interactions as a directed property graph. Powers:
  1. Relationship strength scoring between users
  2. Conversation flow analysis (which topics lead to matches)
  3. Platform effectiveness ranking (which app drives best outcomes)
  4. Recommendation: "Users like you matched best on X platform"
  5. Fraud detection: identify suspicious connection patterns

Storage: In production, use Neo4j or Amazon Neptune.
This implementation uses an in-memory adjacency model for development.
"""

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("platform")


@dataclass
class GraphNode:
    id: str
    node_type: str  # user, platform, conversation, match
    properties: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)


@dataclass
class GraphEdge:
    source: str
    target: str
    edge_type: str  # MESSAGED, MATCHED, CONNECTED_ON, USED_AI, LIKED
    weight: float = 1.0
    properties: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)


class KnowledgeGraph:
    """In-memory property graph for relationship intelligence."""
    
    def __init__(self):
        self._nodes: Dict[str, GraphNode] = {}
        self._edges: List[GraphEdge] = []
        self._adjacency: Dict[str, List[GraphEdge]] = defaultdict(list)
        self._reverse_adjacency: Dict[str, List[GraphEdge]] = defaultdict(list)
    
    # ── Node Operations ─────────────────────────────────────────────────────
    def add_node(self, node_id: str, node_type: str, **properties) -> GraphNode:
        node = GraphNode(id=node_id, node_type=node_type, properties=properties)
        self._nodes[node_id] = node
        return node
    
    def get_node(self, node_id: str) -> Optional[GraphNode]:
        return self._nodes.get(node_id)
    
    # ── Edge Operations ─────────────────────────────────────────────────────
    def add_edge(
        self,
        source: str,
        target: str,
        edge_type: str,
        weight: float = 1.0,
        **properties,
    ) -> GraphEdge:
        edge = GraphEdge(
            source=source, target=target, edge_type=edge_type,
            weight=weight, properties=properties,
        )
        self._edges.append(edge)
        self._adjacency[source].append(edge)
        self._reverse_adjacency[target].append(edge)
        return edge
    
    # ── Queries ─────────────────────────────────────────────────────────────
    def relationship_strength(self, user_a: str, user_b: str) -> float:
        """Compute bidirectional relationship strength score [0, 1].
        
        Factors:
          - Message count (bidirectional)
          - Response time average
          - AI suggestion acceptance on this conversation
          - Conversation duration
        """
        forward = [e for e in self._adjacency.get(user_a, []) if e.target == user_b]
        backward = [e for e in self._adjacency.get(user_b, []) if e.target == user_a]
        
        total_interactions = len(forward) + len(backward)
        if total_interactions == 0:
            return 0.0
        
        # Weighted scoring
        message_score = min(total_interactions / 50, 1.0)  # Cap at 50 messages
        
        # Reciprocity bonus (both sides messaging)
        reciprocity = min(len(forward), len(backward)) / max(len(forward), len(backward), 1)
        
        # Weight by edge types
        match_bonus = 0.3 if any(
            e.edge_type == "MATCHED" for e in forward + backward
        ) else 0.0
        
        ai_used = any(e.edge_type == "USED_AI" for e in forward + backward)
        ai_bonus = 0.1 if ai_used else 0.0
        
        score = (message_score * 0.4 + reciprocity * 0.2 + match_bonus + ai_bonus)
        return round(min(score, 1.0), 3)
    
    def platform_effectiveness(self, user_id: str) -> List[Dict[str, Any]]:
        """Rank platforms by outcome quality for this user."""
        platform_edges = [
            e for e in self._adjacency.get(user_id, [])
            if e.edge_type == "CONNECTED_ON"
        ]
        
        results = []
        for edge in platform_edges:
            platform = edge.target
            
            # Count matches from this platform
            matches = [
                e for e in self._adjacency.get(user_id, [])
                if e.edge_type == "MATCHED" and e.properties.get("platform") == platform
            ]
            
            # Count conversations from this platform  
            conversations = [
                e for e in self._adjacency.get(user_id, [])
                if e.edge_type == "MESSAGED" and e.properties.get("platform") == platform
            ]
            
            match_rate = len(matches) / max(len(conversations), 1)
            
            results.append({
                "platform": platform,
                "total_conversations": len(conversations),
                "total_matches": len(matches),
                "match_rate": round(match_rate, 3),
                "effectiveness_score": round(
                    match_rate * 0.6 + min(len(conversations) / 20, 1.0) * 0.4,
                    3
                ),
            })
        
        results.sort(key=lambda x: x["effectiveness_score"], reverse=True)
        return results
    
    def find_connection_paths(
        self,
        source: str,
        target: str,
        max_depth: int = 3,
    ) -> List[List[str]]:
        """Find all paths between two users (up to max_depth)."""
        paths = []
        
        def dfs(current: str, path: List[str], visited: Set[str]):
            if current == target:
                paths.append(path[:])
                return
            if len(path) >= max_depth:
                return
            
            for edge in self._adjacency.get(current, []):
                if edge.target not in visited:
                    visited.add(edge.target)
                    path.append(edge.target)
                    dfs(edge.target, path, visited)
                    path.pop()
                    visited.remove(edge.target)
        
        dfs(source, [source], {source})
        return paths
    
    def detect_suspicious_patterns(self, user_id: str) -> List[Dict[str, Any]]:
        """Detect potentially fraudulent connection patterns.
        
        Flags:
          - Fan-out: user connecting to >50 users in 24 hours
          - Velocity: >100 messages in 1 hour
          - Reciprocity anomaly: messaging many users with no responses
        """
        alerts = []
        outgoing = self._adjacency.get(user_id, [])
        
        # Fan-out detection
        recent_connections = [
            e for e in outgoing
            if e.edge_type == "MESSAGED" and (time.time() - e.created_at) < 86400
        ]
        unique_targets = len(set(e.target for e in recent_connections))
        if unique_targets > 50:
            alerts.append({
                "type": "high_fan_out",
                "severity": "warning",
                "unique_targets_24h": unique_targets,
                "threshold": 50,
            })
        
        # Message velocity detection
        recent_hour = [
            e for e in outgoing
            if e.edge_type == "MESSAGED" and (time.time() - e.created_at) < 3600
        ]
        if len(recent_hour) > 100:
            alerts.append({
                "type": "high_velocity",
                "severity": "critical",
                "messages_1h": len(recent_hour),
                "threshold": 100,
            })
        
        # Low reciprocity detection (possible spam/bot)
        if unique_targets > 10:
            incoming = self._reverse_adjacency.get(user_id, [])
            incoming_from = set(e.source for e in incoming if e.edge_type == "MESSAGED")
            outgoing_to = set(e.target for e in outgoing if e.edge_type == "MESSAGED")
            reciprocated = incoming_from & outgoing_to
            reciprocity_rate = len(reciprocated) / len(outgoing_to) if outgoing_to else 1.0
            if reciprocity_rate < 0.1:
                alerts.append({
                    "type": "low_reciprocity",
                    "severity": "warning",
                    "reciprocity_rate": round(reciprocity_rate, 3),
                    "messaged_count": len(outgoing_to),
                    "reciprocated_count": len(reciprocated),
                })
        
        return alerts
    
    def get_graph_stats(self) -> Dict[str, Any]:
        return {
            "total_nodes": len(self._nodes),
            "total_edges": len(self._edges),
            "node_types": dict(defaultdict(
                int,
                {n.node_type: sum(1 for _ in filter(
                    lambda x: x.node_type == n.node_type, self._nodes.values()
                )) for n in self._nodes.values()}
            )),
            "edge_types": dict(defaultdict(
                int,
                {e.edge_type: sum(1 for _ in filter(
                    lambda x: x.edge_type == e.edge_type, self._edges
                )) for e in self._edges}
            )),
        }


# Module singleton
knowledge_graph = KnowledgeGraph()
