"""
Disease Hallmarks Package

This package provides tools for analyzing diseases through the lens of aging hallmarks.
"""

from disease_hallmarks.analysis import DiseaseAnalyzer
from disease_hallmarks.models import DiseaseAnnotation, HallmarkScore
from disease_hallmarks.api_callers import GeneOntologyAPI, OpenTargetsAPI
from disease_hallmarks.pathway_agent import PathwayAnalysisAgent
from disease_hallmarks.cache import Cache

__version__ = "0.2.0"

__all__ = [
    'DiseaseAnalyzer',
    'DiseaseAnnotation',
    'HallmarkScores',
    'GeneOntologyAPI',
    'OpenTargetsAPI',
    'PathwayAnalysisAgent',
    'Cache',
]
