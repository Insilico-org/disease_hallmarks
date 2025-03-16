import os
import re
import json
import hashlib
import requests
import tiktoken
from typing import Any, Optional
from functools import lru_cache
from dotenv import load_dotenv
from json_repair import repair_json
from just_agents.base_agent import BaseAgent
from .cache import Cache
from .api_callers import GeneOntologyAPI, QuickGOAPI

def count_tokens(text: str, model: str = "gpt-4") -> int:
    """
    Count the number of tokens in a text string.
    
    Args:
        text: The text to count tokens for
        model: The model to use for tokenization
        
    Returns:
        Number of tokens in the text
    """
    try:
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except Exception:
        # Fallback to approximate token count if tiktoken fails
        return len(text.split()) * 1.3  # Rough approximation

def inspect_pathway(pathway_ID: str, human_only: bool = True, use_quick_go: bool = True) -> dict[str, Any]:
    """
    Look up GO pathway information using the Gene Ontology API or QuickGO API
    
    Args:
        pathway_ID: GO pathway ID (e.g., 'GO:0006915') or pathway name with GO ID in parentheses
                   (e.g., "Glutamate Receptor Signaling Pathway (GO:0007215)")
        human_only: If True, only return annotations for human genes (NCBITaxon:9606)
        use_quick_go: Whether to use QuickGO API (True) or GeneOntologyAPI (False)
        
    Returns:
        Dictionary containing pathway information including:
        - id: The GO ID
        - label: The pathway name
        - definition: The pathway definition
        - annotations: List of genes/proteins annotated with this pathway
        - related_terms: Related GO terms
    """
    # Import here to avoid circular imports
    from .api_callers import GeneOntologyAPI, QuickGOAPI
    
    # Create GO API instance
    if use_quick_go:
        go_api = QuickGOAPI(cache=None)  # Don't use cache here to avoid nested caching
    else:
        go_api = GeneOntologyAPI(cache=None)  # Don't use cache here to avoid nested caching
    
    # Call the inspect_pathway method of the GeneOntologyAPI class
    return go_api.inspect_pathway(pathway_ID, human_only)

class PathwayAnalysisAgent(BaseAgent):
    """Agent for analyzing pathway-hallmark relationships"""
    
    def __init__(self, model: str = "gpt-4", cache: Optional[Cache] = None, max_tokens: int = 7500, use_quick_go: bool = True):
        """
        Initialize the PathwayAnalysisAgent.
        
        Args:
            model: The model to use for pathway analysis
            cache: Optional Cache instance to use for caching API responses
            max_tokens: Maximum tokens for prompt to avoid exceeding context window
            use_quick_go: Whether to use QuickGO API (True) or GeneOntologyAPI (False)
        """

        llm_options = {"model": model}
        super().__init__(llm_options=llm_options,
                         tools=[inspect_pathway])
        
        self.model = model
        
        # Use provided cache or create a new one with TTL from environment
        if cache is None:
            # Load environment variables
            load_dotenv()
            
            # Get cache directory from environment or default
            cache_dir = os.getenv('CACHE_DIR', '.cache')
            
            # Get cache TTL from environment or default
            cache_ttl = os.getenv('CACHE_TTL')
            if cache_ttl is not None:
                try:
                    cache_ttl = int(cache_ttl)
                except ValueError:
                    print(f"Warning: Invalid CACHE_TTL value '{cache_ttl}', using default")
                    cache_ttl = 86400  # 24 hours
            else:
                cache_ttl = 86400  # 24 hours
                
            self.cache = Cache(cache_dir, ttl=cache_ttl)
        else:
            self.cache = cache
            
        # Create llm_options dictionary required by BaseAgent

        self.max_tokens = max_tokens  # Maximum tokens for prompt to avoid exceeding context window

        self.hallmark_descriptions = """
        ## 1. Genomic_instability
        The accumulation of genetic damage throughout life from both exogenous sources (chemicals, radiation, physical stressors) 
        and endogenous challenges (DNA replication errors, reactive oxygen species, spontaneous hydrolytic reactions). 
        This includes point mutations, deletions, translocations, chromosomal rearrangements, and gene disruptions. 
        Genomic instability is characterized by declining efficiency of DNA repair mechanisms with age, affecting 
        nuclear and mitochondrial DNA integrity. Key processes include nuclear architecture maintenance, 
        DNA damage response pathways, and prevention of cytosolic DNA accumulation.

        ## 2. Telomere_attrition
        The progressive shortening of telomeres (protective DNA sequences at chromosome ends) that occurs 
        with each cell division due to the inability of DNA polymerase to completely replicate chromosome ends. 
        When telomeres become critically short, cells undergo senescence or apoptosis. Telomere attrition causes 
        genomic instability, impairs tissue regeneration, and is accelerated by oxidative stress. 
        Telomerase, which can counteract telomere shortening, is not expressed in most somatic cells 
        but its activation can extend lifespan in experimental models.

        ## 3. Epigenetic_alterations
        Age-associated changes in epigenetic patterns that affect gene expression without altering DNA sequence. 
        These include alterations in DNA methylation (global hypomethylation with site-specific hypermethylation), 
        histone modifications (e.g., changes in acetylation and methylation patterns), chromatin remodeling 
        (heterochromatin loss and redistribution), and deregulated expression of non-coding RNAs. 
        Age-related epigenetic changes also include the derepression of retrotransposable elements.

        ## 4. Loss_of_proteostasis
        The progressive failure of protein homeostasis systems with age, leading to accumulation of misfolded, 
        oxidized, or otherwise damaged proteins. This involves deterioration of protein quality control 
        mechanisms including chaperone-mediated folding, the ubiquitin-proteasome system, and lysosomal 
        degradation pathways. Loss of proteostasis is characterized by protein aggregation and inclusion body formation.

        ## 5. Disabled_macroautophagy
        The age-related decline in macroautophagy, a critical cellular process for degrading and recycling 
        dysfunctional organelles, protein aggregates, and other cytoplasmic components via their sequestration 
        in autophagosomes and subsequent fusion with lysosomes. Disabled macroautophagy leads to accumulation 
        of cellular waste and damaged components, particularly affecting long-lived post-mitotic cells. 
        This process is distinct from other forms of autophagy like chaperone-mediated autophagy.

        ## 6. Deregulated_nutrient_sensing
        The progressive dysfunction of nutrient-sensing pathways that coordinate cellular and systemic 
        responses to nutrient availability. Key pathways include insulin/IGF-1 signaling, mTOR (mechanistic target of rapamycin), 
        AMPK (AMP-activated protein kinase), and sirtuins. During aging, these pathways become less responsive to nutritional 
        signals, resulting in metabolic imbalances. Caloric restriction and other dietary interventions that modulate 
        these pathways can extend lifespan in various model organisms.

        ## 7. Mitochondrial_dysfunction
        The age-related decline in mitochondrial function characterized by reduced respiratory efficiency, 
        increased production of reactive oxygen species (ROS), accumulation of mitochondrial DNA mutations, 
        altered mitochondrial dynamics (fusion/fission), and impaired mitophagy. Mitochondrial dysfunction leads 
        to cellular energy deficits, oxidative damage to cellular components, and can trigger stress responses 
        when mitochondrial components leak into the cytosol.

        ## 8. Cellular_senescence
        The state of stable cell cycle arrest combined with phenotypic changes including secretion 
        of pro-inflammatory cytokines, growth factors, and matrix-remodeling enzymes (the senescence-associated 
        secretory phenotype or SASP). Cellular senescence increases with age in multiple tissues and can be triggered 
        by telomere shortening, DNA damage, oncogene activation, or other stressors. 
        While senescence serves as a tumor-suppressive mechanism and aids in wound healing, accumulation of senescent cells 
        contributes to tissue dysfunction and chronic inflammation.

        ## 9. Stem_cell_exhaustion
        The age-related decline in stem cell function across tissues, resulting in reduced regenerative capacity 
        and impaired tissue maintenance. This involves decreased self-renewal abilities, impaired differentiation potential, 
        and diminished responsiveness to tissue needs. Stem cell exhaustion is influenced by intrinsic changes within 
        stem cells themselves (DNA damage, epigenetic alterations, proteostatic decline) and changes in the stem 
        cell niche and systemic environment.

        ## 10. Altered_intercellular_communication
        Age-associated changes in how cells signal to each other, including endocrine, neuroendocrine, and neuronal signaling. 
        This encompasses changes in the systemic milieu (circulating factors), extracellular matrix composition and stiffness, 
        and cell-to-cell contact-dependent communication.

        ## 11. Chronic_inflammation
        The persistent, low-grade, sterile inflammation that develops with age ("inflammaging"),
         characterized by elevated levels of pro-inflammatory cytokines (IL-6, TNF-alpha, IL-1beta) and acute phase proteins like 
         C-reactive protein (CRP). This results from various sources, including accumulation of cellular debris, 
         activation of the innate immune system by cytosolic DNA or other damage-associated molecular patterns, 
         senescence-associated secretory phenotype (SASP), and declining immunosurveillance. 
        """

        self.base_prompt = """
        You are an expert in aging biology and pathway analysis.
        Your task is to analyze biological pathways and determine their relationship
        to the hallmarks of aging.

        The hallmarks' of aging names you can use are:

        1. Genomic_instability
        2. Telomere_attrition
        3. Epigenetic_alterations
        4. Loss_of_proteostasis
        5. Disabled_macroautophagy
        6. Deregulated_nutrient_sensing
        7. Mitochondrial_dysfunction
        8. Cellular_senescence
        9. Stem_cell_exhaustion
        10. Altered_intercellular_communication
        11. Chronic_inflammation

        Here are detailed descriptions of each hallmark to guide your analysis:
        """ + self.hallmark_descriptions + """

        For each pathway, assess its relationship to these hallmarks and return a list 
        of hallmarks to which this pathway belong. Return and empty list if no hallmark 
        associations are detected. Follow this format of presentation (JSON):

        {"full_input_pathway_name" : ["Cellular_senescence", "Stem_cell_exhaustion"]}

        Only return the JSON-formatted output without any additional text.
        """

    
    def analyze_pathway(self, pathway: str) -> list[str]:
        """
        Analyze a pathway's relationship to aging hallmarks.
        
        Args:
            pathway: Pathway name or GO ID
            
        Returns:
            List of hallmarks associated with the pathway
        """
        # Check if we have a cached result
        cache_key = f"gpt4_pathway_analysis_{pathway}"
        if self.cache:
            cached_result = self.cache.get(cache_key)
            if cached_result is not None:
                # Validate that the cached result is a list of strings
                if isinstance(cached_result, list) and all(isinstance(item, str) for item in cached_result):
                    return cached_result
                else:
                    # Clear the invalid cache entry
                    self.cache.delete(cache_key)
                    return []
            
        # Get pathway information from Gene Ontology API using the inspect_pathway tool
        pathway_info = inspect_pathway(pathway, use_quick_go=True)
        
        # Clear the agent's memory to prevent context window overflow
        self.memory.clear_messages()
        
        # Construct a prompt for the agent
        prompt = f"""You are an expert in aging biology and pathway analysis. Your task is to analyze a biological pathway and determine which hallmarks of aging it is associated with.

Pathway: {pathway_info.get('label', pathway)}
GO ID: {pathway_info.get('id', 'Unknown')}
Definition: {pathway_info.get('definition', 'No definition available')}

"""
        
        # Add gene annotations if available (limit to 20 for readability)
        annotations = pathway_info.get('annotations', [])
        if annotations:
            gene_symbols = []
            for ann in annotations:
                if 'gene_symbol' in ann:
                    symbol = ann.get('gene_symbol', '')
                    gene_id = ann.get('gene_id', '')
                    if symbol and gene_id:
                        gene_symbols.append(f"{symbol} ({gene_id})")
                    elif symbol:
                        gene_symbols.append(symbol)
            
            gene_symbols = [s for s in gene_symbols if s]  # Filter out empty strings
            
            if gene_symbols:
                prompt += f"Genes involved in this pathway: {', '.join(gene_symbols[:20])}"
                if len(gene_symbols) > 20:
                    prompt += f" and {len(gene_symbols) - 20} more genes"
                prompt += "\n\n"
        
        # Add related terms if available (limit to 10 for readability)
        related_terms = pathway_info.get('related_terms', [])
        if related_terms:
            # Filter to only include terms with labels
            labeled_terms = [term for term in related_terms if term.get('label') and term.get('label') != 'Unknown']
            
            if labeled_terms:
                prompt += "Related biological processes and functions:\n"
                for i, term in enumerate(labeled_terms[:10]):
                    prompt += f"- {term.get('label', 'Unknown')} ({term.get('relationship', 'related')})\n"
                
                if len(labeled_terms) > 10:
                    prompt += f"- And {len(labeled_terms) - 10} more related terms\n"
                prompt += "\n"
        
        prompt += """Based on the pathway information above, determine which hallmarks of aging are associated with this pathway. The hallmarks of aging are:

1. Genomic_instability
2. Telomere_attrition
3. Epigenetic_alterations
4. Loss_of_proteostasis
5. Disabled_macroautophagy
6. Deregulated_nutrient_sensing
7. Mitochondrial_dysfunction
8. Cellular_senescence
9. Stem_cell_exhaustion
10. Altered_intercellular_communication
11. Chronic_inflammation

Respond with a list of hallmarks that are associated with this pathway. 
If there are no clear associations, return an empty list. 
Format your response as a JSON array of strings.
"""
        
        # Send the prompt to the LLM
        response = self.query(prompt)
        
        # Parse the response to extract the hallmarks
        try:
            # Try to parse the response as JSON
            hallmarks = json.loads(response)
            
            # Validate that the result is a list of strings
            if not isinstance(hallmarks, list):
                hallmarks = []
            
            # Filter out any non-string items
            hallmarks = [h for h in hallmarks if isinstance(h, str)]
            
            # Cache the result
            if self.cache:
                self.cache.set(f"gpt4_pathway_analysis_{pathway}", hallmarks)
            
            return hallmarks
        except json.JSONDecodeError:
            # If JSON parsing fails, try to repair the JSON
            try:
                repaired_json = repair_json(response)
                hallmarks = json.loads(repaired_json)
                
                # Validate that the result is a list of strings
                if not isinstance(hallmarks, list):
                    hallmarks = []
                
                # Filter out any non-string items
                hallmarks = [h for h in hallmarks if isinstance(h, str)]
                
                # Cache the result
                if self.cache:
                    self.cache.set(f"gpt4_pathway_analysis_{pathway}", hallmarks)
                
                return hallmarks
            except Exception as e:
                return []
        except Exception as e:
            return []
    
    def analyze_pathways(
        self, 
        pathways: dict[str, float]
    ) -> dict[str, list[str]]:
        """
        Analyze multiple pathways and their relationships to aging hallmarks
        
        Args:
            pathways: Dictionary mapping pathway names to p-values
            
        Returns:
            Dictionary mapping pathway names to lists of associated aging hallmarks
        """
        results = dict()
        for pathway in pathways:
            results[pathway] = self.analyze_pathway(pathway)
        return results
