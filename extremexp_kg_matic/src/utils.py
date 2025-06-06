import re
import os
import logging
from rdflib import Graph, URIRef, Literal, Namespace
from rdflib.namespace import RDF, RDFS

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define namespaces
EX = Namespace("http://example.org/")

def sanitize_for_uri(text):
    """
    Sanitizes a string to be used as part of a URI.
    Replaces spaces and special characters with underscores.
    """
    if not text:
        return "unknown"
    # Remove special characters, replace spaces with underscores
    text = re.sub(r'[^\w\s-]', '', str(text).strip()) # Keep alphanumeric, whitespace, hyphen
    text = re.sub(r'[-\s]+', '_', text) # Replace one or more hyphens/spaces with a single underscore
    return text if text else "sanitized_empty"

def create_rdf_graph_from_text(file_path: str) -> Graph:
    """
    Create an RDF graph from a text file by extracting relationships.
    
    Args:
        file_path: Path to the text file to process
        
    Returns:
        Graph: An RDF graph containing extracted triples
    """
    graph = Graph()
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            
        logger.info(f"Processing file: {file_path}")
        
        # Extract filename for use as a base entity
        filename = os.path.basename(file_path)
        document_uri = EX[f"document_{filename.replace('.', '_')}"]
        
        # Add document metadata
        graph.add((document_uri, RDF.type, EX.Document))
        graph.add((document_uri, RDFS.label, Literal(filename)))
        graph.add((document_uri, EX.hasContent, Literal(content)))
        
        # Extract simple relationships from the content
        lines = content.split('\n')
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
                
            # Create line entity
            line_uri = EX[f"line_{i+1}"]
            graph.add((line_uri, RDF.type, EX.Line))
            graph.add((line_uri, RDFS.label, Literal(f"Line {i+1}")))
            graph.add((line_uri, EX.hasText, Literal(line)))
            graph.add((document_uri, EX.hasLine, line_uri))
            
            # Extract simple patterns - subject verb object
            # Look for patterns like "A is B" or "A has B"
            patterns = [
                r'(\w+)\s+is\s+(\w+)',
                r'(\w+)\s+has\s+(\w+)',
                r'(\w+)\s+contains\s+(\w+)',
                r'(\w+)\s+includes\s+(\w+)',
                r'(\w+)\s+uses\s+(\w+)',
                r'(\w+)\s+implements\s+(\w+)',
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, line, re.IGNORECASE)
                for match in matches:
                    subject = match[0].lower()
                    obj = match[1].lower()
                    
                    subject_uri = EX[subject]
                    object_uri = EX[obj]
                    
                    # Determine relationship type based on pattern
                    if 'is' in pattern:
                        graph.add((subject_uri, RDF.type, object_uri))
                    elif 'has' in pattern:
                        graph.add((subject_uri, EX.has, object_uri))
                    elif 'contains' in pattern:
                        graph.add((subject_uri, EX.contains, object_uri))
                    elif 'includes' in pattern:
                        graph.add((subject_uri, EX.includes, object_uri))
                    elif 'uses' in pattern:
                        graph.add((subject_uri, EX.uses, object_uri))
                    elif 'implements' in pattern:
                        graph.add((subject_uri, EX.implements, object_uri))
                    
                    # Link to the line where this relationship was found
                    relationship_uri = EX[f"relationship_{subject}_{obj}_{i+1}"]
                    graph.add((relationship_uri, RDF.type, EX.Relationship))
                    graph.add((relationship_uri, EX.hasSubject, subject_uri))
                    graph.add((relationship_uri, EX.hasObject, object_uri))
                    graph.add((relationship_uri, EX.foundInLine, line_uri))
        
        logger.info(f"Created graph with {len(graph)} triples from {file_path}")
        return graph
        
    except Exception as e:
        logger.error(f"Error processing file {file_path}: {str(e)}")
        # Return empty graph on error
        return Graph()

def validate_triple(subject: str, predicate: str, object_value: str) -> bool:
    """
    Validate a triple before adding it to the knowledge graph.
    
    Args:
        subject: Subject of the triple
        predicate: Predicate of the triple
        object_value: Object of the triple
        
    Returns:
        bool: True if valid, False otherwise
    """
    # Basic validation rules
    if not all([subject.strip(), predicate.strip(), object_value.strip()]):
        return False
    
    # Check for minimum length
    if len(subject) < 2 or len(predicate) < 2 or len(object_value) < 2:
        return False
    
    # Check for invalid characters (basic validation)
    invalid_chars = ['<', '>', '"', '\\', '\n', '\r', '\t']
    for char in invalid_chars:
        if char in subject or char in predicate or char in object_value:
            return False
    
    return True

def sanitize_uri(text: str) -> str:
    """
    Sanitize text to create a valid URI.
    
    Args:
        text: Text to sanitize
        
    Returns:
        str: Sanitized text suitable for URI
    """
    # Replace spaces and special characters with underscores
    sanitized = re.sub(r'[^\w\-_]', '_', text)
    # Remove multiple consecutive underscores
    sanitized = re.sub(r'_+', '_', sanitized)
    # Remove leading/trailing underscores
    sanitized = sanitized.strip('_')
    # Ensure it starts with a letter
    if sanitized and not sanitized[0].isalpha():
        sanitized = 'item_' + sanitized
    return sanitized or 'unknown'

def get_year_from_pdf_url(url):
    """
    Extract year from a PDF URL.
    Looks for 4-digit year patterns in the URL, specifically for arXiv URLs.
    
    Args:
        url: The URL string to extract year from
        
    Returns:
        str: The extracted year or None if no year found
    """
    if not url:
        return None
      # Special handling for arXiv URLs like: https://arxiv.org/pdf/1907.11692v1.pdf
    # The arXiv ID format is YYMM.NNNNN where YY is last 2 digits of year, MM is month
    arxiv_pattern = r'arxiv\.org/pdf/(\d{2})(\d{2})\.\d+'
    arxiv_match = re.search(arxiv_pattern, url, re.IGNORECASE)
    if arxiv_match:
        yy = int(arxiv_match.group(1))  # First 2 digits: year
        mm = int(arxiv_match.group(2))  # Next 2 digits: month
        
        # Validate month (01-12)
        if mm < 1 or mm > 12:
            # If month is invalid, fall through to general year pattern matching
            pass
        else:            # Determine century: arXiv started in April 1991
            # If YY >= 91, it's 19XX, otherwise 20XX
            # Special case: YY = 90 should be 1990 (pre-arXiv, but we handle it)
            if yy >= 90:
                year = 1900 + yy
            else:
                year = 2000 + yy
            return str(year)
    
    # Fallback: Look for explicit 4-digit year patterns (1900-2099)
    year_pattern = r'\b(19\d{2}|20\d{2})\b'
    matches = re.findall(year_pattern, url)
    
    if matches:
        # Return the last occurrence of a year pattern
        return matches[-1]
    
    return None

def create_rdf_graph_from_papers(papers_data: list) -> Graph:
    """
    Create an RDF graph from papers data structure.
    
    Args:
        papers_data: List of paper dictionaries
        
    Returns:
        Graph: An RDF graph containing the paper data as triples
    """
    from rdflib import Graph, Literal, URIRef, RDF, XSD
    from kg_schema import (
        EX, Paper, Task, Dataset, Method, ModelConfiguration, ReportedResult,
        paper_title, paper_pdfUrl, paper_papersWithCodeUrl, paper_year,
        task_name, dataset_name, method_name, mc_configurationString,
        rr_metricName, rr_metricValue, rr_rank,
        paper_mentionsTask, paper_mentionsDataset, paper_reportsResult, paper_employsMethod,
        rr_evaluatesTask, rr_onDataset, rr_achievedByModel, rr_reportedInPaper
    )
    
    g = Graph()
    uri_cache = {}
    def get_uri(entity_type_ns, name_part, base_ns=EX):
        """Creates or retrieves a URI for an entity."""
        sanitized_name = sanitize_for_uri(name_part)
        
        # Extract the class name from the URIRef
        if hasattr(entity_type_ns, '__name__'):
            class_name = entity_type_ns.__name__
        else:
            # For URIRef objects, get the last part after the namespace
            class_name = str(entity_type_ns).split('/')[-1].split('#')[-1]
        
        cache_key = f"{class_name}_{sanitized_name}"
        
        if cache_key not in uri_cache:
            uri_cache[cache_key] = URIRef(base_ns[f"{class_name}_{sanitized_name}"])
        return uri_cache[cache_key]
    
    # Process each paper
    for paper_data in papers_data:
        if not isinstance(paper_data, dict):
            logger.warning(f"Skipping invalid paper data: {paper_data}")
            continue
            
        # Create unique URI for this paper
        paper_title_str = paper_data.get("title", "Unknown")
        paper_uri_name = sanitize_for_uri(paper_title_str)
        paper_uri = URIRef(EX[f"Paper_{paper_uri_name}"])
        g.add((paper_uri, RDF.type, Paper))

        # Add paper properties
        if paper_data.get("title"):
            g.add((paper_uri, paper_title, Literal(paper_data["title"], datatype=XSD.string)))
        
        if paper_data.get("url") or paper_data.get("pdfUrl"):
            pdf_url = paper_data.get("url") or paper_data.get("pdfUrl")
            g.add((paper_uri, paper_pdfUrl, Literal(pdf_url, datatype=XSD.anyURI)))
            year = get_year_from_pdf_url(pdf_url)
            if year:
                g.add((paper_uri, paper_year, Literal(year, datatype=XSD.gYear)))
        
        if paper_data.get("year"):
            g.add((paper_uri, paper_year, Literal(paper_data["year"], datatype=XSD.gYear)))
            
        if paper_data.get("origin") or paper_data.get("papersWithCodeUrl"):
            pwc_url = paper_data.get("origin") or paper_data.get("papersWithCodeUrl")
            g.add((paper_uri, paper_papersWithCodeUrl, Literal(pwc_url, datatype=XSD.anyURI)))

        # Add tasks
        tasks = paper_data.get("tasks", [])
        if isinstance(tasks, str):
            tasks = [tasks]
        for task_str in tasks:
            task_uri = get_uri(Task, task_str)
            g.add((task_uri, RDF.type, Task))
            g.add((task_uri, task_name, Literal(task_str, datatype=XSD.string)))
            g.add((paper_uri, paper_mentionsTask, task_uri))

        # Add datasets
        datasets = paper_data.get("datasets", [])
        if isinstance(datasets, str):
            datasets = [datasets]
        for dataset_str in datasets:
            dataset_uri = get_uri(Dataset, dataset_str)
            g.add((dataset_uri, RDF.type, Dataset))
            g.add((dataset_uri, dataset_name, Literal(dataset_str, datatype=XSD.string)))
            g.add((paper_uri, paper_mentionsDataset, dataset_uri))

        # Add methods
        methods = paper_data.get("methods", [])
        if isinstance(methods, str):
            methods = [methods]
        for method_str in methods:
            method_uri = get_uri(Method, method_str)
            g.add((method_uri, RDF.type, Method))
            g.add((method_uri, method_name, Literal(method_str, datatype=XSD.string)))
            g.add((paper_uri, paper_employsMethod, method_uri))
            
        # Add results
        results = paper_data.get("results", [])
        if isinstance(results, dict):
            results = [results]
        for result_idx, result_data in enumerate(results):
            result_uri_name = f"{paper_uri_name}_result_{result_idx}"
            result_uri = URIRef(EX[result_uri_name])
            g.add((result_uri, RDF.type, ReportedResult))
            g.add((paper_uri, paper_reportsResult, result_uri))
            g.add((result_uri, rr_reportedInPaper, paper_uri))

            if result_data.get("metric"):
                g.add((result_uri, rr_metricName, Literal(result_data["metric"], datatype=XSD.string)))
                
            if result_data.get("value"):
                value_str = str(result_data["value"])
                if "%" in value_str:
                    try:
                        numeric_val = float(value_str.replace("%", "").strip())
                        g.add((result_uri, rr_metricValue, Literal(numeric_val / 100.0, datatype=XSD.decimal)))
                    except ValueError:
                        g.add((result_uri, rr_metricValue, Literal(value_str, datatype=XSD.string)))
                else:
                    try:
                        g.add((result_uri, rr_metricValue, Literal(float(value_str), datatype=XSD.decimal)))
                    except ValueError:
                        g.add((result_uri, rr_metricValue, Literal(value_str, datatype=XSD.string)))

            if result_data.get("rank"):
                try:
                    g.add((result_uri, rr_rank, Literal(int(result_data["rank"]), datatype=XSD.integer)))
                except ValueError:
                    logger.warning(f"Could not parse rank '{result_data['rank']}' as integer")

            # Link result to task
            if result_data.get("task"):
                res_task_uri = get_uri(Task, result_data["task"])
                g.add((res_task_uri, RDF.type, Task))
                g.add((res_task_uri, task_name, Literal(result_data["task"])))
                g.add((result_uri, rr_evaluatesTask, res_task_uri))

            # Link result to dataset
            if result_data.get("dataset"):
                res_dataset_uri = get_uri(Dataset, result_data["dataset"])
                g.add((res_dataset_uri, RDF.type, Dataset))
                g.add((res_dataset_uri, dataset_name, Literal(result_data["dataset"])))
                g.add((result_uri, rr_onDataset, res_dataset_uri))
            
            # Link result to model
            if result_data.get("model"):
                model_config_str = result_data["model"]
                mc_uri = get_uri(ModelConfiguration, model_config_str)
                g.add((mc_uri, RDF.type, ModelConfiguration))
                g.add((mc_uri, mc_configurationString, Literal(model_config_str, datatype=XSD.string)))
                g.add((result_uri, rr_achievedByModel, mc_uri))
    
    logger.info(f"Created RDF graph with {len(g)} triples from {len(papers_data)} papers")
    return g
