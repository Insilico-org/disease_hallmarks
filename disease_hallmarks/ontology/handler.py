"""
Ontology API handler
"""
import json
import requests
from functools import lru_cache
from typing import Optional, Dict, Any

from .sources import OntologySource

class OntologyHandler:
    """Handles interactions with ontology APIs"""
    
    def __init__(self, source: OntologySource = OntologySource.OLS):
        self.source = source
        self.session = requests.Session()
        
    @lru_cache(maxsize=1000)
    def search_term(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Search for a term in the ontology
        
        Args:
            query: Search term
            
        Returns:
            Dictionary with term info or None if not found
        """
        if self.source == OntologySource.OLS:
            return self._search_ols(query)
        else:
            raise ValueError(f"Unsupported ontology source: {self.source}")
            
    def _search_ols(self, query: str) -> Optional[Dict[str, Any]]:
        """Search using OLS API"""
        url = f"https://www.ebi.ac.uk/ols/api/search"
        params = {
            "q": query,
            "ontology": "efo",
            "fieldList": "id,iri,label,short_form,obo_id",
            "rows": 10
        }
        
        response = self.session.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        # Find best match
        if not data["response"]["docs"]:
            return None
            
        for doc in data["response"]["docs"]:
            if doc["ontology_name"] == "efo":
                return {
                    "id": doc["short_form"],
                    "iri": doc["iri"],
                    "label": doc["label"],
                    "obo_id": doc.get("obo_id")
                }
                
        return None
