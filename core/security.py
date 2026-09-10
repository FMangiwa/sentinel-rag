"""
core/security.py
Enforces Multi-Tenant Isolation and Role-Based Access Control (RBAC)
by generating metadata filters for ChromaDB.
"""

from typing import Dict, Any, List, Set
from config import cfg

class SecurityContext:
    def __init__(self, tenant_id: str, user_role: str):
        self.tenant_id = tenant_id
        self.user_role = user_role.lower()
        self.allowed_classifications = self._compute_allowed_classifications()

    def _compute_allowed_classifications(self) -> Set[str]:
        """Look up allowed classifications based on user role from Config."""
        return cfg.ROLE_PERMISSIONS.get(
            self.user_role, 
            cfg.ROLE_PERMISSIONS["guest"] # Fallback to lowest privilege
        )

    def build_chroma_where_clause(self) -> Dict[str, Any]:
        """
        Constructs ChromaDB 'where' filter syntax enforcing both:
        1. Tenant ID strict matching
        2. Clearance classification level filtering
        """
        classifications = list(self.allowed_classifications)
        
        # Base condition: Tenant matching
        tenant_filter = {"tenant_id": {"$eq": self.tenant_id}}
        
        # Classification filter
        if len(classifications) == 1:
            class_filter = {"classification": {"$eq": classifications[0]}}
        else:
            class_filter = {"classification": {"$in": classifications}}

        # Combine conditions using Chroma's $and operator
        return {
            "$and": [
                tenant_filter,
                class_filter
            ]
        }

    def filter_bm25_corpus(self, corpus: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filters memory-resident BM25 corpus to match tenant security context.
        """
        filtered = []
        for doc in corpus:
            meta = doc.get("metadata", {})
            if meta.get("tenant_id") == self.tenant_id and \
               meta.get("classification") in self.allowed_classifications:
                filtered.append(doc)
        return filtered


if __name__ == "__main__":
    # Test Security Verification
    sec_admin = SecurityContext(tenant_id="InsureLLM", user_role="admin")
    sec_guest = SecurityContext(tenant_id="InsureLLM", user_role="guest")
    
    print("Admin Chroma Filter:", sec_admin.build_chroma_where_clause())
    print("Guest Chroma Filter:", sec_guest.build_chroma_where_clause())