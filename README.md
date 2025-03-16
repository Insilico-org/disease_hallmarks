# Disease Hallmarks Analysis

A tool for analyzing diseases through the lens of aging hallmarks. This project enables:

- Decomposing diseases by their association with hallmarks of aging
- Comparing diseases based on their aging-related characteristics
- Scoring diseases based on their relevance to aging processes

## Installation

### From GitHub

```bash
git clone https://github.com/yourusername/disease_hallmarks.git
cd disease_hallmarks
pip install -e .
```

### Dependencies

```bash
pip install -r requirements.txt
```

## Features

- Disease lookup via EFO identifiers
- Target gene retrieval from OpenTargets
- Analysis against published hallmark genes
- Integration with GenAge longevity database
- GO pathway enrichment analysis
- AI-powered hallmark association analysis
- Pathway score normalization based on hallmark distribution
- Visualization of results with Plotly
- Caching system for API responses

## Project Structure

- `models.py` - Core data classes for disease annotations, hallmark scores, and the disease database
- `analysis.py` - Main analysis logic for processing diseases and calculating aging hallmark scores
- `cache.py` - Caching system for API responses to avoid redundant calls
- `pathway_agent.py` - AI agent for analyzing pathway-hallmark relationships
- `hallmark_genes.py` - Pre-defined lists of genes associated with each hallmark of aging
- `api_callers.py` - Dedicated classes for interacting with external APIs
- `cache_manager.py` - Utilities for managing and inspecting the cache

## Environment Setup

1. Copy the `.env_demo` file to `.env`:
```bash
cp .env_demo .env
```

2. Edit `.env` and fill in your API keys and preferences:
- `OPENAI_API_KEY`: Your OpenAI API key (required for pathway analysis)
- `CACHE_DIR`: Directory for caching API responses (optional)
- `PATHWAY_AGENT_MODEL`: GPT model to use (default: gpt-4)

## Configuration

The application can be configured using environment variables or a `.env` file in the project root. Here are the available configuration options:

### Cache Configuration

- `CACHE_DIR`: Directory to store cache files (default: `materials/query_cache`)
- `CACHE_TTL`: Time-to-live for cache entries in seconds (default: 86400 seconds / 24 hours)
  - Set to `-1` for infinite TTL (never expire)
To use the precomputed cache, unpack `query_cache.tar`

### API Model Configuration

- `PATHWAY_AGENT_MODEL`: Model to use for pathway analysis (default: `gpt-4`)

### Example .env file

```
# Disease Hallmarks Configuration

# Cache settings
CACHE_DIR=materials/query_cache
CACHE_TTL=-1  # -1 means infinite (never expire)

# API model settings
PATHWAY_AGENT_MODEL=gpt-4
```

## Usage

```python
from disease_hallmarks.analysis import DiseaseAnalyzer

# Create analyzer instance
analyzer = DiseaseAnalyzer()

# Analyze a single disease
results = analyzer.analyze_disease("Alzheimer's disease")

# Compare two diseases
comparison = analyzer.compare_diseases("Alzheimer's disease", "Parkinson's disease")
```

## Moving Cache Files

If you have existing cache files in a different location, you can use the provided script to move them to the new location:

```bash
python scripts/move_cache.py --source old/folder --target new/folder --overwrite
```

Or simply set the `CACHE_DIR` environment variable to point to your existing cache location.

## Pathway Normalization

The system now includes a pathway normalization feature that improves the accuracy of hallmark scores by accounting for the distribution of pathways across different hallmarks. This addresses the issue where hallmarks with many annotated pathways might receive inflated scores simply due to their higher representation in pathway databases.

### How it works

1. The system precomputes hallmark annotations for all pathways in the GO database
2. For each hallmark, it calculates a normalization factor based on the total number of pathways associated with that hallmark
3. During disease analysis, pathway scores are adjusted using these normalization factors
4. This ensures that hallmarks are scored based on their biological relevance rather than their representation in pathway databases

### Using the normalization feature

To precompute pathway annotations:

```bash
python scripts/precompute_pathway_annotations.py --go-file materials/GO_Molecular_Function_2023
```

The precomputed annotations are stored in the cache directory and automatically used during disease analysis.

To see the effect of normalization on disease analysis:

```bash
python examples/normalization_demo.py "Alzheimer's disease"
```

## Cache Management

The application includes a cache management system to help inspect, analyze, and clear the cache. This is useful for troubleshooting and maintenance.

### Using the Cache Manager

Use the wrapper script from the command line:

```bash
python scripts/manage_cache.py [command] [options]
```

### Cache Types

The cache manager recognizes the following types of cached API requests:

- `enrichr`: Enrichr API responses for pathway enrichment analysis
- `ols`: EBI Ontology Lookup Service responses
- `opentargets`: Open Targets Platform API responses
- `go`: Gene Ontology and QuickGO API responses
- `gpt4`: GPT-4 pathway analysis responses
- `other`: Other API responses not fitting into the above categories

### Programmatic Cache Management

You can also manage the cache programmatically in your code:

```python
from disease_hallmarks.cache import Cache

# Initialize cache
cache = Cache('.cache')

# Analyze cache
cache.print_analysis()

# List cache items by type
items = cache.list_cache_by_type('enrichr')

# Clear cache by type
cleared = cache.clear_cache_by_type('enrichr')

# Clear disease-specific cache
cleared = cache.clear_disease_cache("Alzheimer's disease")

# Clear expired cache
cleared = cache.clear_expired()
```

See the `examples/cache_management_example.py` file for a complete example.

## Data Sources

- EFO (Experimental Factor Ontology)
- OpenTargets Platform
- GenAge Database
- Aging-us.com published hallmark genes
- Gene Ontology (via Enrichr)

## License

MIT
