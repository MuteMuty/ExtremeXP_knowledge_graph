import json
import sys
import time
from rdflib import Graph, Literal, URIRef, RDF, XSD
from kg_schema import (
    EX, Paper, Task, Dataset, Method, ModelConfiguration, ReportedResult,
    paper_title, paper_pdfUrl, paper_papersWithCodeUrl, paper_year,
    task_name, dataset_name, method_name, mc_configurationString,
    rr_metricName, rr_metricValue, rr_rank,
    paper_mentionsTask, paper_mentionsDataset, paper_reportsResult, paper_employsMethod,
    rr_evaluatesTask, rr_onDataset, rr_achievedByModel, rr_reportedInPaper
)
from utils import sanitize_for_uri, get_year_from_pdf_url
from fuseki_client import FusekiClient
from file_watcher import FileWatcherService
import os

# --- Configuration ---
# INPUT_JSON_PATH = "../data/five_papers.json" # Adjust if your script is elsewhere
# OUTPUT_ RDF_PATH = "../data/output.ttl"
INPUT_JSON_PATH = "/app/data/five_papers.json"
OUTPUT_RDF_PATH = "/app/data/output.ttl"
OUTPUT_FORMAT = "turtle" # or "xml", "n3", "nt"

# --- Helper to manage URIs and avoid duplicates ---
uri_cache = {}

def get_uri(entity_type_ns, name_part, base_ns=EX):
    """Creates or retrieves a URI for an entity."""
    sanitized_name = sanitize_for_uri(name_part)
    
    # Extract the local name (e.g., "Paper", "Task") from the URIRef
    class_local_name = str(entity_type_ns).split('/')[-1].split('#')[-1]
    
    cache_key = (class_local_name, sanitized_name) # Use the string local name for the cache key
    if cache_key in uri_cache:
        return uri_cache[cache_key]
    
    new_uri = URIRef(f"{base_ns}{class_local_name}_{sanitized_name}") # Use extracted local name
    uri_cache[cache_key] = new_uri
    return new_uri

def create_rdf_graph(papers_data):
    g = Graph()
    # Bind prefixes for nicer output
    g.bind("ex", EX)
    g.bind("rdf", RDF)
    g.bind("xsd", XSD)

    for paper_idx, paper_data in enumerate(papers_data):
        paper_uri_name = sanitize_for_uri(paper_data.get("title", f"paper_{paper_idx}"))
        paper_uri = URIRef(EX[f"Paper_{paper_uri_name}"]) # Unique URI for the paper
        g.add((paper_uri, RDF.type, Paper))

        if paper_data.get("title"):
            g.add((paper_uri, paper_title, Literal(paper_data["title"], datatype=XSD.string)))
        if paper_data.get("url"): # PDF URL
            g.add((paper_uri, paper_pdfUrl, Literal(paper_data["url"], datatype=XSD.anyURI)))
            year = get_year_from_pdf_url(paper_data["url"])
            if year:
                 g.add((paper_uri, paper_year, Literal(year, datatype=XSD.gYear)))
        if paper_data.get("origin"): # PapersWithCode URL
            g.add((paper_uri, paper_papersWithCodeUrl, Literal(paper_data["origin"], datatype=XSD.anyURI)))

        # --- Tasks ---
        for task_str in paper_data.get("tasks", []):
            task_uri = get_uri(Task, task_str)
            g.add((task_uri, RDF.type, Task))
            g.add((task_uri, task_name, Literal(task_str, datatype=XSD.string)))
            g.add((paper_uri, paper_mentionsTask, task_uri))

        # --- Datasets ---
        for dataset_str in paper_data.get("datasets", []):
            dataset_uri = get_uri(Dataset, dataset_str)
            g.add((dataset_uri, RDF.type, Dataset))
            g.add((dataset_uri, dataset_name, Literal(dataset_str, datatype=XSD.string)))
            g.add((paper_uri, paper_mentionsDataset, dataset_uri))

        # --- Methods (general) ---
        for method_str in paper_data.get("methods", []):
            method_uri = get_uri(Method, method_str)
            g.add((method_uri, RDF.type, Method))
            g.add((method_uri, method_name, Literal(method_str, datatype=XSD.string)))
            g.add((paper_uri, paper_employsMethod, method_uri))
            
        # --- Results ---
        for result_idx, result_data in enumerate(paper_data.get("results", [])):
            # Create a unique URI for each result object
            result_uri_name = f"{paper_uri_name}_result_{result_idx}"
            result_uri = URIRef(EX[result_uri_name])
            g.add((result_uri, RDF.type, ReportedResult))
            g.add((paper_uri, paper_reportsResult, result_uri)) # Link paper to this result
            g.add((result_uri, rr_reportedInPaper, paper_uri)) # Inverse link

            if result_data.get("metric"):
                g.add((result_uri, rr_metricName, Literal(result_data["metric"], datatype=XSD.string)))
            if result_data.get("value"):
                # Handle potential '%' in value
                value_str = str(result_data["value"])
                if "%" in value_str:
                    try:
                        # Store numeric part as float, and maybe add a unit property later
                        numeric_val = float(value_str.replace("%", "").strip())
                        g.add((result_uri, rr_metricValue, Literal(numeric_val / 100.0, datatype=XSD.decimal))) # Store as ratio
                        # Or store as string: g.add((result_uri, rr_metricValue, Literal(value_str, datatype=XSD.string)))
                    except ValueError:
                        g.add((result_uri, rr_metricValue, Literal(value_str, datatype=XSD.string))) # Fallback to string
                else:
                    try:
                        g.add((result_uri, rr_metricValue, Literal(float(value_str), datatype=XSD.decimal)))
                    except ValueError:
                        g.add((result_uri, rr_metricValue, Literal(value_str, datatype=XSD.string))) # Fallback

            if result_data.get("rank"):
                try:
                    g.add((result_uri, rr_rank, Literal(int(result_data["rank"]), datatype=XSD.integer)))
                except ValueError:
                    print(f"Warning: Could not parse rank '{result_data['rank']}' as integer for {result_uri}")


            # Link result to its specific task
            if result_data.get("task"):
                res_task_uri = get_uri(Task, result_data["task"])
                g.add((res_task_uri, RDF.type, Task)) # Ensure type declaration if new
                g.add((res_task_uri, task_name, Literal(result_data["task"])))
                g.add((result_uri, rr_evaluatesTask, res_task_uri))

            # Link result to its specific dataset
            if result_data.get("dataset"):
                res_dataset_uri = get_uri(Dataset, result_data["dataset"])
                g.add((res_dataset_uri, RDF.type, Dataset)) # Ensure type declaration if new
                g.add((res_dataset_uri, dataset_name, Literal(result_data["dataset"])))
                g.add((result_uri, rr_onDataset, res_dataset_uri))
            
            # Link result to its specific model configuration
            if result_data.get("model"):
                model_config_str = result_data["model"]
                # Create a unique URI for ModelConfiguration based on its string
                mc_uri = get_uri(ModelConfiguration, model_config_str)
                g.add((mc_uri, RDF.type, ModelConfiguration))
                g.add((mc_uri, mc_configurationString, Literal(model_config_str, datatype=XSD.string)))
                g.add((result_uri, rr_achievedByModel, mc_uri))
    return g

if __name__ == "__main__":
    # Check if we should run in service mode (default) or one-time mode
    mode = os.environ.get("RUN_MODE", "service")  # "service" or "oneshot"
    data_dir = "/app/data"
    if mode == "service":
        print("Starting ExtremeXP KG API Service...")
        
        # Initialize Fuseki client and wait for it to be available
        fuseki_client = FusekiClient()
        if not fuseki_client.wait_for_fuseki():
            print("ERROR: Fuseki is not available. Exiting.")
            sys.exit(1)
        
        print("Fuseki is ready. Starting FastAPI server...")
        
        # Start the FastAPI server
        import uvicorn
        import api
        
        # Run the FastAPI server
        uvicorn.run(
            "api:app",
            host="0.0.0.0", 
            port=8000, 
            log_level="info",
            reload=False
        )
            
    else:  # oneshot mode - original functionality
        print("Running in one-shot mode...")
        
        # Ensure data directory exists for output
        os.makedirs(os.path.dirname(OUTPUT_RDF_PATH), exist_ok=True)

        try:
            with open(INPUT_JSON_PATH, 'r', encoding='utf-8') as f:
                all_papers_data = json.load(f)
        except FileNotFoundError:
            print(f"Error: Input JSON file not found at {INPUT_JSON_PATH}")
            sys.exit(1)
        except json.JSONDecodeError:
            print(f"Error: Could not decode JSON from {INPUT_JSON_PATH}")
            sys.exit(1)

        rdf_graph = create_rdf_graph(all_papers_data)
        
        try:
            rdf_graph.serialize(destination=OUTPUT_RDF_PATH, format=OUTPUT_FORMAT, encoding="utf-8")
            print(f"RDF graph successfully generated and saved to {OUTPUT_RDF_PATH} (Format: {OUTPUT_FORMAT})")
        except Exception as e:
            print(f"Error serializing RDF graph: {e}")
            sys.exit(1)
