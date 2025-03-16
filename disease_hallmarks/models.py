from dataclasses import dataclass, field
from typing import Dict, List, Optional
from dataclasses_json import dataclass_json
from datetime import datetime

@dataclass_json
@dataclass
class HallmarkScore:
    """Score for a specific hallmark of aging"""
    name: str
    gene_overlap_score: float = 0.0  # Score based on direct gene overlaps
    pathway_score: float = 0.0  # Score based on pathway analysis
    total_score: float = 0.0  # Combined score
    overlapping_genes: list[str] = field(default_factory=list)
    relevant_pathways: list[str] = field(default_factory=list)

@dataclass_json
@dataclass
class DiseaseAnnotation:
    """Stores disease analysis results and scores"""
    name: str
    efo_id: str
    target_genes: list[str] = field(default_factory=list)
    hallmark_scores: Dict[str, HallmarkScore] = field(default_factory=dict)
    longevity_genes: list[str] = field(default_factory=list)
    enriched_pathways: Dict[str, float] = field(default_factory=dict)  # pathway -> p-value
    total_aging_score: float = 0.0
    analysis_date: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def get_top_hallmarks(self, n: int = 3) -> List[tuple[str, float]]:
        """Get top n hallmarks by total score"""
        return sorted(
            [(h.name, h.total_score) for h in self.hallmark_scores.values()],
            key=lambda x: x[1],
            reverse=True
        )[:n]

@dataclass_json
@dataclass
class DiseaseDB:
    """Database of analyzed diseases with query capabilities"""
    diseases: Dict[str, DiseaseAnnotation] = field(default_factory=dict)
    
    def add_disease(self, disease: DiseaseAnnotation):
        """Add or update a disease annotation"""
        self.diseases[disease.efo_id] = disease
    
    def get_by_hallmark(self, hallmark: str, min_score: float = 0.0) -> List[DiseaseAnnotation]:
        """Get diseases with specified hallmark score above threshold"""
        return sorted(
            [d for d in self.diseases.values() 
             if d.hallmark_scores.get(hallmark, HallmarkScore(hallmark)).total_score > min_score],
            key=lambda x: x.hallmark_scores[hallmark].total_score,
            reverse=True
        )
    
    def get_by_total_score(self, min_score: float = 0.0) -> List[DiseaseAnnotation]:
        """Get diseases with total aging score above threshold"""
        return sorted(
            [d for d in self.diseases.values() if d.total_aging_score > min_score],
            key=lambda x: x.total_aging_score,
            reverse=True
        )
