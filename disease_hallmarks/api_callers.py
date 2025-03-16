# agents/api_callers.py
from typing import Optional, Union
import json
import requests
import hashlib

from time import sleep
from functools import lru_cache
from threading import Lock

from typing import Optional, List, Dict, Any, Optional, ClassVar
from chembl_webresource_client.new_client import new_client

from dataclasses import dataclass, field
import re


class EnrichrCaller:
    """Handles API calls to Enrichr pathway analysis service"""

    BASE_URL: str = 'https://maayanlab.cloud/Enrichr'
    # see all options here: https://maayanlab.cloud/Enrichr/datasetStatistics
    DEFAULT_DB: str = "GO_Biological_Process_2023"

    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0, cache=None, timeout: float = 30.0, debug: bool = False):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.cache = cache
        self.timeout = timeout  # Add timeout parameter
        self.debug = debug      # Add debug flag



    def add_list(self, gene_list: List[str], desc: str = "NA") -> Optional[str]:
        """Submit gene list to Enrichr"""
        # Convert gene list to string
        genes_str = '\n'.join(gene_list)
        
        # Updated URL format to match Enrichr API documentation
        url = f"{self.BASE_URL}/addList"
        
        if self.debug:
            print(f"[DEBUG] Enrichr API URL: {url}")
        
        # Create cache key based on the gene list
        cache_key = f"enrichr_add_list_{hashlib.md5(genes_str.encode()).hexdigest()}_{desc}"
        
        # Check cache first if available
        if self.cache:
            cached_result = self.cache.get(cache_key)
            if cached_result and not isinstance(cached_result, Exception):
                if self.debug:
                    print(f"[DEBUG] Using cached Enrichr list ID: {cached_result}")
                return cached_result
        
        payload = {
            'list': (None, genes_str),
            'description': (None, desc)
        }

        for attempt in range(self.max_retries):
            if self.debug:
                print(f"[DEBUG] Enrichr add_list attempt {attempt+1}/{self.max_retries} - {len(gene_list)} genes")
                
            try:
                response = requests.post(url, files=payload, timeout=self.timeout)
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        if "userListId" in data:
                            list_id = data["userListId"]
                            
                            # Cache the result if cache is available
                            if self.cache:
                                self.cache.set(cache_key, list_id)
                                
                            if self.debug:
                                print(f"[DEBUG] Successfully got Enrichr list ID: {list_id}")
                                
                            return list_id
                        else:
                            error_msg = f"No userListId in response: {data}"
                            if self.debug:
                                print(f"[DEBUG] Enrichr API error: {error_msg}")
                    except json.JSONDecodeError:
                        error_msg = f"Invalid JSON response: {response.text[:100]}"
                        if self.debug:
                            print(f"[DEBUG] Enrichr API JSON error: {error_msg}")
                else:
                    error_msg = f"HTTP error {response.status_code}: {response.text[:100]}"
                    if self.debug:
                        print(f"[DEBUG] Enrichr API HTTP error: {error_msg}")
                        
            except requests.exceptions.Timeout:
                error_msg = f"Request timed out after {self.timeout}s"
                if self.debug:
                    print(f"[DEBUG] Enrichr API timeout: {error_msg}")
            except requests.exceptions.ConnectionError as e:
                error_msg = f"Connection error: {str(e)}"
                if self.debug:
                    print(f"[DEBUG] Enrichr API connection error: {error_msg}")
            except Exception as e:
                error_msg = f"Unexpected error: {str(e)}"
                if self.debug:
                    print(f"[DEBUG] Enrichr API unexpected error: {error_msg}")
                
            # If we get here, there was an error
            if attempt < self.max_retries - 1:
                if self.debug:
                    print(f"[DEBUG] Retrying in {self.retry_delay} seconds...")
                sleep(self.retry_delay)
            else:
                # Last attempt failed, return an error
                error = Exception(f"Error submitting gene list to Enrichr: {error_msg}")
                
                # Cache the error if cache is available
                if self.cache:
                    # Don't cache errors
                    pass
                    
                return error
                
        # This should never be reached due to the return in the loop
        return Exception("Unknown error in Enrichr add_list")

    def view_list(self, list_id: str) -> Optional[List[str]]:
        """View gene list from Enrichr"""
        # Updated URL format to match Enrichr API documentation
        url = f"{self.BASE_URL}/view?userListId={list_id}"
        
        if self.debug:
            print(f"[DEBUG] Enrichr API URL: {url}")
        
        # Create cache key
        cache_key = f"enrichr_view_list_{list_id}"
        
        # Check cache first if available
        if self.cache:
            cached_result = self.cache.get(cache_key)
            if cached_result and not isinstance(cached_result, Exception):
                if self.debug:
                    print(f"[DEBUG] Using cached Enrichr view list result")
                return cached_result
        
        for attempt in range(self.max_retries):
            if self.debug:
                print(f"[DEBUG] Enrichr view_list attempt {attempt+1}/{self.max_retries} - list ID: {list_id}")
                
            try:
                response = requests.get(url, timeout=self.timeout)
                
                if response.status_code == 200:
                    try:
                        genes = response.json()
                        
                        # Cache the result if cache is available
                        if self.cache:
                            self.cache.set(cache_key, genes)
                            
                        if self.debug:
                            print(f"[DEBUG] Successfully retrieved gene list with {len(genes)} genes")
                            
                        return genes
                    except json.JSONDecodeError:
                        error_msg = f"Invalid JSON response: {response.text[:100]}"
                        if self.debug:
                            print(f"[DEBUG] Enrichr API JSON error: {error_msg}")
                else:
                    error_msg = f"HTTP error {response.status_code}: {response.text[:100]}"
                    if self.debug:
                        print(f"[DEBUG] Enrichr API HTTP error: {error_msg}")
                        
            except requests.exceptions.Timeout:
                error_msg = f"Request timed out after {self.timeout}s"
                if self.debug:
                    print(f"[DEBUG] Enrichr API timeout: {error_msg}")
            except requests.exceptions.ConnectionError as e:
                error_msg = f"Connection error: {str(e)}"
                if self.debug:
                    print(f"[DEBUG] Enrichr API connection error: {error_msg}")
            except Exception as e:
                error_msg = f"Unexpected error: {str(e)}"
                if self.debug:
                    print(f"[DEBUG] Enrichr API unexpected error: {error_msg}")
                
            # If we get here, there was an error
            if attempt < self.max_retries - 1:
                if self.debug:
                    print(f"[DEBUG] Retrying in {self.retry_delay} seconds...")
                sleep(self.retry_delay)
            else:
                # Last attempt failed, return an error
                error = Exception(f"Error retrieving gene list from Enrichr: {error_msg}")
                
                # Cache the error if cache is available
                if self.cache:
                    # Don't cache errors
                    pass
                    
                return error
                
        # This should never be reached due to the return in the loop
        return Exception("Unknown error in Enrichr view_list")

    def enrich(self, list_id: str, gene_set_library: str = None) -> Optional[Dict]:
        """Get enrichment results from Enrichr"""
        gene_set_library = gene_set_library or self.DEFAULT_DB
        
        # Updated URL format to match Enrichr API documentation
        url = f"{self.BASE_URL}/enrich?userListId={list_id}&backgroundType={gene_set_library}"
        
        if self.debug:
            print(f"[DEBUG] Enrichr API URL: {url}")
        
        # Create cache key
        cache_key = f"enrichr_enrich_{list_id}_{gene_set_library}"
        
        # Check cache first if available
        if self.cache:
            cached_result = self.cache.get(cache_key)
            if cached_result and not isinstance(cached_result, Exception):
                if self.debug:
                    print(f"[DEBUG] Using cached Enrichr enrichment result")
                return cached_result
        
        for attempt in range(self.max_retries):
            if self.debug:
                print(f"[DEBUG] Enrichr enrich attempt {attempt+1}/{self.max_retries} - list ID: {list_id}, library: {gene_set_library}")
                
            try:
                response = requests.get(url, timeout=self.timeout)
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        
                        # Cache the result if cache is available
                        if self.cache:
                            self.cache.set(cache_key, data)
                            
                        if self.debug:
                            result_count = len(data.get(gene_set_library, []))
                            print(f"[DEBUG] Successfully retrieved enrichment results with {result_count} items")
                            
                        return data
                    except json.JSONDecodeError:
                        error_msg = f"Invalid JSON response: {response.text[:100]}"
                        if self.debug:
                            print(f"[DEBUG] Enrichr API JSON error: {error_msg}")
                else:
                    error_msg = f"HTTP error {response.status_code}: {response.text[:100]}"
                    if self.debug:
                        print(f"[DEBUG] Enrichr API HTTP error: {error_msg}")
                        
            except requests.exceptions.Timeout:
                error_msg = f"Request timed out after {self.timeout}s"
                if self.debug:
                    print(f"[DEBUG] Enrichr API timeout: {error_msg}")
            except requests.exceptions.ConnectionError as e:
                error_msg = f"Connection error: {str(e)}"
                if self.debug:
                    print(f"[DEBUG] Enrichr API connection error: {error_msg}")
            except Exception as e:
                error_msg = f"Unexpected error: {str(e)}"
                if self.debug:
                    print(f"[DEBUG] Enrichr API unexpected error: {error_msg}")
                
            # If we get here, there was an error
            if attempt < self.max_retries - 1:
                if self.debug:
                    print(f"[DEBUG] Retrying in {self.retry_delay} seconds...")
                sleep(self.retry_delay)
            else:
                # Last attempt failed, return an error
                error = Exception(f"Error retrieving enrichment results from Enrichr: {error_msg}")
                
                # Cache the error if cache is available
                if self.cache:
                    # Don't cache errors
                    pass
                    
                return error
                
        # This should never be reached due to the return in the loop
        return Exception("Unknown error in Enrichr enrich")

    def analyze(self, gene_list: List[str], desc: str = "NA", background_type: Optional[str] = None) -> Dict[str, Any]:
        """Analyze gene list with Enrichr"""
        if self.debug:
            print(f"[DEBUG] Starting Enrichr analysis for {len(gene_list)} genes")
            
        # Submit gene list
        list_id = self.add_list(gene_list, desc)
        
        # Check if list_id is an exception
        if isinstance(list_id, Exception):
            if self.debug:
                print(f"[DEBUG] Enrichr analysis failed at add_list step: {str(list_id)}")
            return list_id
        
        # Get enrichment results
        results = self.enrich(list_id, background_type)
        
        # Check if results is an exception
        if isinstance(results, Exception):
            if self.debug:
                print(f"[DEBUG] Enrichr analysis failed at enrich step: {str(results)}")
            return results
            
        if self.debug:
            print(f"[DEBUG] Enrichr analysis completed successfully")
            
        return results


class EnrichrAnalysis:
    """Wrapper for pathway enrichment analysis with result parsing"""

    legend: tuple[str] = (
        'Rank', 'Term name', 'P-value', 'Odds ratio',
        'Combined score', 'Overlapping genes', 'Adjusted p-value',
        'Old p-value', 'Old adjusted p-value'
    )

    def __init__(self, gene_list: List[str], cache=None, description: str = "NA", debug: bool = False):
        self.gene_list = gene_list
        self.description = description
        self.results = None
        self.debug = debug
        
        # Create Enrichr caller with longer timeout and debug mode if requested
        self.enrichr = EnrichrCaller(
            max_retries=5,  # Increase retries
            retry_delay=2.0,  # Longer delay between retries
            cache=cache,
            timeout=60.0,  # Increase timeout to 60 seconds
            debug=debug
        )
        
    def analyze(self) -> None:
        """Run analysis"""
        if self.debug:
            print(f"Starting Enrichr analysis for {len(self.gene_list)} genes")
            
        self.results = self.enrichr.analyze(self.gene_list, self.description)
        
        if isinstance(self.results, Exception):
            print(f"Enrichr analysis failed: {str(self.results)}")
        elif self.debug:
            print(f"Enrichr analysis completed successfully")
            
    def get_significant_terms(self,
                              p_value_threshold: float = 0.05,
                              min_overlap: int = 2) -> List[Dict[str, Any]]:
        """Extract significant enriched terms"""
        if not self.results:
            return []

        significant = []
        for term in self.results.get(self.enrichr.DEFAULT_DB, []):
            overlapping_genes = term[5] if isinstance(term[5], list) else [term[5]]
            if (term[2] < p_value_threshold and
                len(overlapping_genes) >= min_overlap):
                significant.append({
                    'term': term[1],
                    'p_value': term[2],
                    'odds_ratio': term[3],
                    'genes': overlapping_genes
                })

        return sorted(significant, key=lambda x: x['p_value'])

@dataclass
class PubChemCache:
    synonyms: Dict[int, List[str]] = field(default_factory=dict)
    descriptions: Dict[int, List[str]] = field(default_factory=dict)
    chembl_ids: Dict[int, str] = field(default_factory=dict)
    names: Dict[int, str] = field(default_factory=dict)
    cids: Dict[str, int] = field(default_factory=dict)

class PubChemAPI:
    """Thread-safe singleton PubChem API manager with caching"""

    _instance: ClassVar[Optional['PubChemAPI']] = None
    _lock: ClassVar[Lock] = Lock()
    MAX_SYNONYMS = 50

    ENDPOINTS = {
        'cids': "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{}/cids/JSON",
        'synonyms': "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{}/synonyms/JSON",
        'description': "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{}/description/JSON"
    }
    URL_MAX_LENGTH = 2000

    def __new__(cls, *args, **kwargs) -> 'PubChemAPI':
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance

    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0):
        """Initialize only once due to singleton pattern"""
        if not hasattr(self, 'initialized'):
            self.max_retries = max_retries
            self.retry_delay = retry_delay
            self.cache = PubChemCache()
            self.initialized = True

    def _calculate_batch_size(self, items: list[str], base_url: str) -> int:
        """Calculate maximum batch size based on URL length limit"""
        url_overhead = len(base_url.format(""))
        item_overhead = 1
        max_items = (self.URL_MAX_LENGTH - url_overhead) // (max(len(str(x)) for x in items) + item_overhead)
        return min(max_items, 100)

    @lru_cache(maxsize=1000)
    def _make_request(self, endpoint: str, query: str, parser: callable):
        """Cached request handler"""
        retry_count = 0
        while retry_count < self.max_retries:
            try:
                response = requests.get(endpoint.format(query))
                if response.status_code == 200:
                    return parser(response)
                elif response.status_code == 404:
                    return None
                elif response.status_code == 503:
                    retry_count += 1
                    sleep(self.retry_delay)
                    continue
                else:
                    return None
            except requests.RequestException:
                retry_count += 1
                sleep(self.retry_delay)
                continue
        return None

    def _make_batched_request(self,
                              endpoint: str,
                              items: list[str],
                              parser: callable,
                              join_char: str = ",") -> Optional[dict]:
        """Make batched requests with cache filtering"""
        batch_size = self._calculate_batch_size(items, endpoint)
        results = {}

        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            batch_str = join_char.join(batch)

            batch_result = self._make_request(endpoint, batch_str, parser)
            if batch_result:
                results.update(batch_result)

        return results if results else None

    def _format_compound_name(self, name: str) -> str:
        """Format compound name for API query"""
        query = name.strip().lower().replace("-", " ")
        if query.endswith("hcl") and not query.endswith(" hcl"):
            query = query.removesuffix("hcl") + " hcl"
        return query

    def _validate_cid(self, cid: Union[int, str]) -> str:
        """Validate and format CID"""
        cid = str(cid)
        if not cid.isnumeric():
            raise ValueError(f"Invalid CID format: {cid}")
        return cid

    def get_cids_batch(self, names: list[str]) -> Optional[dict[str, str]]:
        """Get PubChem CIDs for multiple compound names"""
        formatted_names = [self._format_compound_name(name) for name in names]
        results = {}

        # First check cache
        uncached_names = []
        for name in formatted_names:
            if name in self.cache.cids:
                results[name] = str(self.cache.cids[name])
            else:
                uncached_names.append(name)

        # Query API only for uncached names
        for name in uncached_names:
            def parse_cids(response: requests.Response) -> Optional[str]:
                data = json.loads(response.text)
                cids = data.get('IdentifierList', {}).get('CID', [])
                if cids:
                    cid = int(cids[0])
                    # Cache name->CID mapping
                    with self._lock:
                        self.cache.cids[name] = cid
                    return str(cid)
                return None

            cid = self._make_request(self.ENDPOINTS['cids'], name, parse_cids)
            if cid:
                results[name] = cid

        return results if results else None

    def get_synonyms_batch(self, cids: list[Union[int, str]]) -> Optional[dict[int, list[str]]]:
        """Get synonyms with caching and CHEMBL ID extraction"""
        validated_cids = [int(self._validate_cid(cid)) for cid in cids]
        uncached_cids = [cid for cid in validated_cids if cid not in self.cache.synonyms]

        if uncached_cids:
            def parse_synonyms(response: requests.Response) -> dict[int, list[str]]:
                data = json.loads(response.text)
                results = {}
                for info in data.get('InformationList', {}).get('Information', []):
                    cid = info.get('CID')
                    if not cid:
                        continue

                    all_synonyms = info.get('Synonym', [])
                    if all_synonyms:
                        # First cache CHEMBL ID from full list if present
                        with self._lock:
                            chembl_ids = [x for x in all_synonyms if x.startswith("CHEMBL")]
                            if chembl_ids:
                                self.cache.chembl_ids[int(cid)] = chembl_ids[0]

                        # Then truncate synonyms list and cache primary name
                        truncated_synonyms = all_synonyms[:self.MAX_SYNONYMS]
                        results[int(cid)] = truncated_synonyms
                        with self._lock:
                            self.cache.names[int(cid)] = truncated_synonyms[0]
                return results

            new_results = self._make_batched_request(
                self.ENDPOINTS['synonyms'],
                [str(cid) for cid in uncached_cids],
                parse_synonyms
            )

            if new_results:
                with self._lock:
                    self.cache.synonyms.update(new_results)

        return {cid: self.cache.synonyms[cid]
                for cid in validated_cids
                if cid in self.cache.synonyms}

    def get_descriptions_batch(self, cids: list[Union[int, str]]) -> Optional[dict[int, list[str]]]:
        """Get descriptions with caching"""
        validated_cids = [int(self._validate_cid(cid)) for cid in cids]
        uncached_cids = [cid for cid in validated_cids if cid not in self.cache.descriptions]

        if uncached_cids:
            def parse_descriptions(response: requests.Response) -> dict[int, list[str]]:
                data = json.loads(response.text)
                results = {}
                for info in data.get('InformationList', {}).get('Information', []):
                    cid = info.get('CID')
                    if not cid:
                        continue

                    descriptions = []
                    if 'Title' in info:
                        descriptions.append(info['Title'])
                    if 'Description' in info:
                        descriptions.append(info['Description'])

                    if descriptions:
                        results[int(cid)] = descriptions
                return results

            new_results = self._make_batched_request(
                self.ENDPOINTS['description'],
                [str(cid) for cid in uncached_cids],
                parse_descriptions
            )

            if new_results:
                with self._lock:
                    self.cache.descriptions.update(new_results)

        return {cid: self.cache.descriptions[cid]
                for cid in validated_cids
                if cid in self.cache.descriptions}

    def get_chembl_ids_batch(self, cids: list[Union[int, str]]) -> Optional[dict[int, str]]:
        """Get CHEMBL IDs (cached during synonym retrieval)"""
        validated_cids = [int(self._validate_cid(cid)) for cid in cids]
        uncached_cids = [cid for cid in validated_cids if cid not in self.cache.chembl_ids]

        if uncached_cids:
            self.get_synonyms_batch(uncached_cids)

        return {cid: self.cache.chembl_ids[cid]
                for cid in validated_cids
                if cid in self.cache.chembl_ids}

    def get_names_batch(self, cids: list[Union[int, str]]) -> Optional[dict[int, str]]:
        """Get primary names (cached during synonym retrieval)"""
        validated_cids = [int(self._validate_cid(cid)) for cid in cids]
        uncached_cids = [cid for cid in validated_cids if cid not in self.cache.names]

        if uncached_cids:
            self.get_synonyms_batch(uncached_cids)

        return {cid: self.cache.names[cid]
                for cid in validated_cids
                if cid in self.cache.names}


@dataclass
class CHEMBL_Annotation:
    chembl_id: str
    parent_id: Optional[str] = None
    activities: List[Dict[str, Any]] = None
    safety_warnings: List[Dict[str, Any]] = None
    indications: List[Dict[str, Any]] = None

    description: Optional[str] = None
    name: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'chembl_id': self.chembl_id,
            'parent_id': self.parent_id,
            'activities': self.activities or [],
            'safety_warnings': self.safety_warnings or [],
            'indications': self.indications or []
        }

    def add_desc(self, name: str, desc: str):
        self.name = name
        self.description = desc


# can't make use of list queries with __in due to pagination limits(

class ChemblBulkAPI:
    def __init__(self):
        self.molecule_client = new_client.molecule_form
        self.activity_client = new_client.activity
        self.safety_client = new_client.drug_warning
        self.indication_client = new_client.drug_indication

    def get_parent_molecules(self, chembl_ids: List[str]) -> Dict[str, str]:
        results = {}
        for chembl_id in chembl_ids:
            response = self.molecule_client.filter(
                molecule_chembl_id=chembl_id
            ).only(['molecule_chembl_id', 'parent_chembl_id'])

            for item in response[0:1]:
                mol_id = item.get('molecule_chembl_id')
                parent_id = item.get('parent_chembl_id')
                if mol_id and parent_id:
                    results[mol_id] = parent_id
        return results

    def get_activities(self, parent_ids: List[str], limit: int = 10) -> Dict[str, List[Dict]]:
        results = {}
        for parent_id in parent_ids:
            response = self.activity_client.filter(
                parent_molecule_chembl_id=parent_id
            ).only(['parent_molecule_chembl_id', 'assay_description'])

            results[parent_id] = [item for item in response[:limit]]
        return results

    def get_safety_warnings(self, parent_ids: List[str], limit: int = 10) -> Dict[str, List[Dict]]:
        results = {}
        for parent_id in parent_ids:
            response = self.safety_client.filter(
                parent_molecule_chembl_id=parent_id
            ).only(['parent_molecule_chembl_id', 'warning_class'])

            results[parent_id] = [item for item in response[:limit]]
        return results

    def get_indications(self, parent_ids: List[str], limit: int = 10) -> Dict[str, List[Dict]]:
        results = {}
        for parent_id in parent_ids:
            response = self.indication_client.filter(
                parent_molecule_chembl_id=parent_id
            ).only(['parent_molecule_chembl_id', 'efo_term', 'max_phase_for_ind'])

            results[parent_id] = [item for item in response[:limit]]
        return results

    def create_annotations(self, chembl_ids: List[str], limit: int = 10) -> List[CHEMBL_Annotation]:
        annotations = []
        parent_mappings = self.get_parent_molecules(chembl_ids)
        parent_ids = list(set(parent_mappings.values()))

        activities = self.get_activities(parent_ids, limit)
        warnings = self.get_safety_warnings(parent_ids, limit)
        indications = self.get_indications(parent_ids, limit)

        for chembl_id in chembl_ids:
            parent_id = parent_mappings.get(chembl_id)
            annotation = CHEMBL_Annotation(
                chembl_id=chembl_id,
                parent_id=parent_id,
                activities=activities.get(parent_id, []),
                safety_warnings=warnings.get(parent_id, []),
                indications=indications.get(parent_id, [])
            )
            annotations.append(annotation)

        return annotations


class GeneOntologyAPI:
    """Handles API calls to Gene Ontology (GO) service"""
    
    BASE_URL: str = "https://api.geneontology.org/api"
    
    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0, cache=None):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.cache = cache
    
    def inspect_pathway(self, pathway_ID: str, human_only: bool = True) -> dict[str, Any]:
        """
        Look up GO pathway information using the Gene Ontology API
        
        Args:
            pathway_ID: GO pathway ID (e.g., 'GO:0006915') or pathway name with GO ID in parentheses
                       (e.g., "Glutamate Receptor Signaling Pathway (GO:0007215)")
            human_only: If True, only return annotations for human genes (NCBITaxon:9606)
            
        Returns:
            Dictionary containing pathway information including:
            - id: The GO ID
            - label: The pathway name
            - definition: The pathway definition
            - annotations: List of genes/proteins annotated with this pathway
            - related_terms: Related GO terms
        """
        # Create a cache key based on the pathway_ID and human_only flag
        cache_key = f"go_pathway_{pathway_ID}_{human_only}"
        
        # Check cache first if available
        if self.cache:
            cached_result = self.cache.get(cache_key)
            if cached_result:
                return cached_result
                
        # Extract GO ID from pathway_ID
        go_id = None
        pathway_name = None
        
        # Check for GO ID in parentheses
        go_id_match = re.search(r'\(GO:(\d+)\)', pathway_ID)
        if go_id_match:
            go_id = f"GO:{go_id_match.group(1)}"
            pathway_name = pathway_ID.split('(GO:')[0].strip()
        elif pathway_ID.startswith('GO:'):
            go_id = pathway_ID
        elif re.match(r'^\d+$', pathway_ID):
            go_id = f"GO:{pathway_ID}"
        else:
            pathway_name = pathway_ID
            
        # If no GO ID found, search for it by name
        if go_id is None:
            try:
                search_response = requests.get(
                    f"{self.BASE_URL}/search/entity/{pathway_name}",
                    params={"category": "ontology", "rows": 5}
                )
                search_data = search_response.json()
                
                # Find first result with GO ID
                for doc in search_data.get("docs", []):
                    if doc.get("id", "").startswith("GO:"):
                        go_id = doc["id"]
                        break
                        
                if go_id is None:
                    error_result = {"id": None, "label": pathway_name, "error": f"Could not find GO ID for pathway: {pathway_name}", "status": "error"}
                    if self.cache:
                        self.cache.set(cache_key, error_result)
                    return error_result
            except Exception as e:
                error_result = {"id": None, "label": pathway_name, "error": str(e), "status": "error"}
                if self.cache:
                    self.cache.set(cache_key, error_result)
                return error_result
        
        # Initialize result dictionary
        result = {
            "id": go_id,
            "label": pathway_name or "",
            "definition": "",
            "annotations": [],
            "related_terms": []
        }
        
        try:
            # Get term information
            term_response = requests.get(f"{self.BASE_URL}/ontology/term/{go_id}")
            term_data = term_response.json()
            
            # Update result with term data
            if term_data:
                result["label"] = term_data.get("label", result["label"])
                result["definition"] = term_data.get("definition", {}).get("val", "")
                
                # Get related terms
                if "relationships" in term_data:
                    for rel_type, terms in term_data["relationships"].items():
                        for term in terms:
                            result["related_terms"].append({
                                "id": term.get("id", ""),
                                "label": term.get("lbl", ""),
                                "relationship": rel_type
                            })
            
            # Get annotations (genes/proteins)
            taxon_filter = "NCBITaxon:9606" if human_only else None
            
            annotation_params = {
                "rows": 100,
                "facet": False
            }
            
            if taxon_filter:
                annotation_params["taxon"] = taxon_filter
                
            annotation_response = requests.get(
                f"{self.BASE_URL}/bioentity/function/{go_id}",
                params=annotation_params
            )
            
            annotation_data = annotation_response.json()
            
            if "associations" in annotation_data:
                for assoc in annotation_data["associations"]:
                    # Extract gene/protein information
                    bioentity = assoc.get("subject", {})
                    
                    annotation = {
                        "gene_id": bioentity.get("id", ""),
                        "gene_symbol": bioentity.get("label", ""),
                        "taxon": bioentity.get("taxon", {}).get("label", "")
                    }
                    
                    result["annotations"].append(annotation)
            
            # Cache the result if cache is available
            if self.cache:
                self.cache.set(cache_key, result)
                
            return result
            
        except Exception as e:
            error_result = {
                "id": go_id,
                "label": result["label"],
                "error": str(e),
                "status": "error"
            }
            if self.cache:
                self.cache.set(cache_key, error_result)
            return error_result


class QuickGOAPI:
    """Handles API calls to QuickGO service (EBI)"""
    
    BASE_URL: str = "https://www.ebi.ac.uk/QuickGO/services"
    
    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0, cache=None):
        """
        Initialize the QuickGO API client
        
        Args:
            max_retries: Maximum number of retries for API calls
            retry_delay: Delay between retries in seconds
            cache: Optional Cache instance to use for caching API responses
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.cache = cache
    
    def inspect_pathway(self, pathway_ID: str, human_only: bool = True) -> dict[str, Any]:
        """
        Look up GO pathway information using the QuickGO API
        
        Args:
            pathway_ID: GO pathway ID (e.g., 'GO:0006915') or pathway name with GO ID in parentheses
                       (e.g., "Glutamate Receptor Signaling Pathway (GO:0007215)")
            human_only: If True, only return annotations for human genes (NCBITaxon:9606)
            
        Returns:
            Dictionary containing pathway information including:
            - id: The GO ID
            - label: The pathway name
            - definition: The pathway definition
            - annotations: List of genes/proteins annotated with this pathway
            - related_terms: Related GO terms (children)
        """
        # Create a cache key based on the pathway_ID and human_only flag
        cache_key = f"quickgo_pathway_{pathway_ID}_{human_only}"
        
        # Check cache first if available
        if self.cache:
            cached_result = self.cache.get(cache_key)
            if cached_result:
                print(f"DEBUG: Using cached result for {pathway_ID}")
                return cached_result
        
        print(f"DEBUG: Fetching new data from QuickGO API for {pathway_ID}")
        
        # Extract GO ID from pathway_ID
        go_id = None
        pathway_name = None
        
        # Check for GO ID in parentheses
        go_id_match = re.search(r'\(GO:(\d+)\)', pathway_ID)
        if go_id_match:
            go_id = f"GO:{go_id_match.group(1)}"
            pathway_name = pathway_ID.split('(GO:')[0].strip()
        elif pathway_ID.startswith('GO:'):
            go_id = pathway_ID
        elif re.match(r'^\d+$', pathway_ID):
            go_id = f"GO:{pathway_ID}"
        else:
            pathway_name = pathway_ID
            
        # If no GO ID found, search for it by name
        if go_id is None:
            try:
                # Search for the GO term by name
                search_url = f"{self.BASE_URL}/search"
                search_params = {
                    "query": pathway_name,
                    "limit": 5,
                    "page": 1
                }
                
                search_response = requests.get(search_url, params=search_params)
                search_data = search_response.json()
                
                # Find first result with GO ID
                go_id = None
                for result in search_data.get("results", []):
                    if result.get("id", "").startswith("GO:"):
                        go_id = result.get("id")
                        break
                        
                if go_id is None:
                    error_result = {"id": None, "label": pathway_name, "error": f"Could not find GO ID for pathway: {pathway_name}", "status": "error"}
                    if self.cache:
                        self.cache.set(cache_key, error_result)
                    return error_result
            except Exception as e:
                error_result = {"id": None, "label": pathway_name, "error": str(e), "status": "error"}
                if self.cache:
                    self.cache.set(cache_key, error_result)
                return error_result
        
        # Initialize result dictionary
        result = {
            "id": go_id,
            "label": pathway_name or "",
            "definition": "",
            "annotations": [],
            "related_terms": []
        }
        
        try:
            # Get term information using the ontology endpoint
            term_url = f"{self.BASE_URL}/ontology/go/terms/{go_id}"
            term_response = requests.get(term_url)
            
            if term_response.status_code != 200:
                error_result = {
                    "id": go_id,
                    "label": result["label"],
                    "error": f"Error retrieving term information: {term_response.status_code}",
                    "status": "error"
                }
                if self.cache:
                    self.cache.set(cache_key, error_result)
                return error_result
                
            term_data = term_response.json()
            
            # Update result with term data
            if term_data and "results" in term_data and len(term_data["results"]) > 0:
                term_info = term_data["results"][0]
                result["label"] = term_info.get("name", result["label"])
                
                # Get definition
                if "definition" in term_info and "text" in term_info["definition"]:
                    result["definition"] = term_info["definition"]["text"]
                
                # Get children as related terms
                if "children" in term_info:
                    # Collect all child IDs to fetch their labels in a batch
                    child_ids = [child.get("id", "") for child in term_info["children"] if "id" in child]
                    child_labels = {}
                    
                    # If we have child IDs, fetch their labels
                    if child_ids:
                        # Fetch labels for child terms in batches of 20
                        for i in range(0, len(child_ids), 20):
                            batch_ids = child_ids[i:i+20]
                            child_terms_url = f"{self.BASE_URL}/ontology/go/terms/{','.join(batch_ids)}"
                            try:
                                child_terms_response = requests.get(child_terms_url)
                                if child_terms_response.status_code == 200:
                                    child_terms_data = child_terms_response.json()
                                    for child_term in child_terms_data.get("results", []):
                                        child_labels[child_term.get("id")] = child_term.get("name", "")
                            except Exception:
                                # Continue even if we can't get labels for some terms
                                pass
                    
                    # Add children with labels if available
                    for child in term_info["children"]:
                        child_id = child.get("id", "")
                        result["related_terms"].append({
                            "id": child_id,
                            "label": child_labels.get(child_id, "Unknown"),
                            "relationship": child.get("relation", "")
                        })
            
            # Get annotations (genes/proteins) using the annotation endpoint
            annotation_url = f"{self.BASE_URL}/annotation/search"
            annotation_params = {
                "goId": go_id,
                "limit": 50,  # Limit to 50 genes - more than this is likely not useful for the agent
                "page": 1
            }
            
            # Add taxon filter if human_only is True
            if human_only:
                annotation_params["taxonId"] = "9606"  # Human taxon ID
                
            annotation_response = requests.get(annotation_url, params=annotation_params)
            
            if annotation_response.status_code == 200:
                annotation_data = annotation_response.json()
                
                if "results" in annotation_data:
                    # Process annotations to extract gene symbols
                    unique_genes = set()  # Use a set to avoid duplicates
                    
                    for anno in annotation_data["results"]:
                        # Prefer gene symbol over UniProt ID
                        gene_symbol = anno.get("symbol", "")
                        
                        # Only add if we have a gene symbol and it's not already in our list
                        if gene_symbol and gene_symbol not in unique_genes:
                            unique_genes.add(gene_symbol)
                            
                            # Extract gene ID from geneProductId (strip UniProtKB: prefix if present)
                            gene_id = anno.get("geneProductId", "")
                            if ":" in gene_id:
                                gene_id = gene_id.split(":", 1)[1]
                            
                            annotation = {
                                "gene_symbol": gene_symbol,
                                "gene_id": gene_id,
                                "taxon": anno.get("taxonName", "")
                            }
                            result["annotations"].append(annotation)
            
            # Cache the result if cache is available
            if self.cache:
                self.cache.set(cache_key, result)
                
            return result
            
        except Exception as e:
            error_result = {
                "id": go_id,
                "label": result["label"],
                "error": str(e),
                "status": "error"
            }
            if self.cache:
                self.cache.set(cache_key, error_result)
            return error_result


class OpenTargetsAPI:
    """Handles API calls to Open Targets Platform API"""
    
    BASE_URL: str = "https://api.platform.opentargets.org/api/v4"
    
    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0, cache=None):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.cache = cache
    
    def search_target(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """
        Search for targets (genes/proteins) by name or symbol
        
        Args:
            query: Target name or symbol to search for
            limit: Maximum number of results to return
            
        Returns:
            Dictionary containing search results
        """
        # Create a cache key
        cache_key = f"ot_target_search_{query}_{limit}"
        
        # Check cache first if available
        if self.cache:
            cached_result = self.cache.get(cache_key)
            if cached_result:
                return cached_result
        
        url = f"{self.BASE_URL}/search"
        params = {
            "q": query,
            "size": limit,
            "filter": "target"
        }
        
        for _ in range(self.max_retries):
            try:
                response = requests.get(url, params=params)
                if response.ok:
                    result = response.json()
                    
                    # Cache the result if cache is available
                    if self.cache:
                        self.cache.set(cache_key, result)
                        
                    return result
                
                if response.status_code != 503:
                    break
                    
            except requests.RequestException:
                pass
                
            sleep(self.retry_delay)
            
        raise Exception(f"Error searching for target: {query}")
    
    def get_target_info(self, target_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a target
        
        Args:
            target_id: Ensembl ID of the target
            
        Returns:
            Dictionary containing target information
        """
        # Create a cache key
        cache_key = f"ot_target_info_{target_id}"
        
        # Check cache first if available
        if self.cache:
            cached_result = self.cache.get(cache_key)
            if cached_result:
                return cached_result
                
        url = f"{self.BASE_URL}/target/{target_id}"
        
        for _ in range(self.max_retries):
            try:
                response = requests.get(url)
                if response.ok:
                    result = response.json()
                    
                    # Cache the result if cache is available
                    if self.cache:
                        self.cache.set(cache_key, result)
                        
                    return result
                
                if response.status_code != 503:
                    break
                    
            except requests.RequestException:
                pass
                
            sleep(self.retry_delay)
            
        raise Exception(f"Error getting target info: {target_id}")
    
    def get_disease_associations(self, target_id: str, limit: int = 10) -> Dict[str, Any]:
        """
        Get diseases associated with a target
        
        Args:
            target_id: Ensembl ID of the target
            limit: Maximum number of results to return
            
        Returns:
            Dictionary containing disease associations
        """
        # Create a cache key
        cache_key = f"ot_target_diseases_{target_id}_{limit}"
        
        # Check cache first if available
        if self.cache:
            cached_result = self.cache.get(cache_key)
            if cached_result:
                return cached_result
                
        url = f"{self.BASE_URL}/target/{target_id}/disease"
        params = {
            "size": limit
        }
        
        for _ in range(self.max_retries):
            try:
                response = requests.get(url, params=params)
                if response.ok:
                    result = response.json()
                    
                    # Cache the result if cache is available
                    if self.cache:
                        self.cache.set(cache_key, result)
                        
                    return result
                
                if response.status_code != 503:
                    break
                    
            except requests.RequestException:
                pass
                
            sleep(self.retry_delay)
            
        raise Exception(f"Error getting disease associations for target: {target_id}")

    def get_disease_targets(self, efo_id: str, max_targets: int = 200, score_threshold: float = 0.0) -> list[str]:
        """
        Get target genes associated with a disease
        
        Args:
            efo_id: EFO ID of the disease
            max_targets: Maximum number of targets to retrieve (default: 200)
            score_threshold: Minimum association score to include a target (0.0-1.0, default: 0.0)
            
        Returns:
            List of gene symbols associated with the disease
        """
        # Create a standardized cache key - use a consistent format to avoid duplicates
        # Always use the same max_targets value in the cache key to prevent duplicate caching
        # The actual max_targets parameter will still be respected in the result
        cache_key = f"ot_disease_targets_{efo_id}_score{score_threshold}"
        
        # Check cache first if available
        if self.cache:
            cached_result = self.cache.get(cache_key)
            if cached_result:
                # Apply the max_targets limit to the cached result
                return cached_result[:max_targets]
        
        all_targets = []
        page_size = 100  # Fetch 100 targets per request
        current_page = 0
        
        while len(all_targets) < max_targets:
            query = """
            query diseaseAssociations($efoId: String!, $index: Int!, $size: Int!) {
              disease(efoId: $efoId) {
                associatedTargets(page: { index: $index, size: $size }) {
                  count
                  rows {
                    target {
                      approvedSymbol
                    }
                    score
                  }
                }
              }
            }
            """
            url = f"{self.BASE_URL}/graphql"
            
            for _ in range(self.max_retries):
                try:
                    response = requests.post(
                        url, 
                        json={"query": query, "variables": {"efoId": efo_id, "index": current_page, "size": page_size}}
                    )
                    
                    if response.ok:
                        data = response.json()
                        
                        try:
                            rows = data["data"]["disease"]["associatedTargets"]["rows"]
                            total_count = data["data"]["disease"]["associatedTargets"]["count"]
                            
                            # Extract target symbols and scores from the current page
                            # Filter by score threshold
                            for row in rows:
                                symbol = row["target"]["approvedSymbol"]
                                score = row["score"]
                                
                                if score >= score_threshold:
                                    all_targets.append(symbol)
                            
                            # If we got fewer targets than requested or reached the total count, we're done
                            if len(rows) < page_size or len(all_targets) >= total_count:
                                break
                                
                            # Move to the next page
                            current_page += 1
                            
                            # Continue to the next page
                            break
                        except (KeyError, TypeError):
                            # No more data available
                            break
                    
                    if response.status_code != 503:
                        break
                        
                except requests.RequestException:
                    pass
                    
                sleep(self.retry_delay)
            else:
                # All retries failed
                break
        
        result = all_targets[:max_targets]  # Limit to max_targets
        
        # Cache the result if cache is available
        if self.cache:
            self.cache.set(cache_key, result)
            
        return result


def main():

    processor = ChemblBulkAPI()
    compounds = ["CHEMBL25", "CHEMBL192", "CHEMBL140"]
    res = processor.create_annotations(compounds)

    pubchem = PubChemAPI()
    cids = pubchem.get_cids_batch(['aspirin', 'paracetamol', 'ibuprofen', 'curcumin'])
    syns = pubchem.get_synonyms_batch([2244])
    pubchem.get_synonyms_batch([2244])
    pubchem.get_names_batch([2244])