"""
Fuseki client for uploading RDF data directly to the triplestore.
"""
import requests
import time
import os
import base64
from typing import Optional
from rdflib import Graph

class FusekiClient:
    def __init__(self, fuseki_url: str = "http://fuseki:3030", dataset: str = "matic_papers_kg"):
        self.fuseki_url = fuseki_url
        self.dataset = dataset
        self.upload_url = f"{fuseki_url}/{dataset}/data"
        self.query_url = f"{fuseki_url}/{dataset}/sparql"
        
    def wait_for_fuseki(self, max_retries: int = 30, delay: int = 2) -> bool:
        """Wait for Fuseki to be available."""
        print("Waiting for Fuseki to be available...")
        for attempt in range(max_retries):
            try:
                response = requests.get(f"{self.fuseki_url}/$/ping", timeout=5)
                if response.status_code == 200:
                    print("Fuseki is available!")
                    return True
            except requests.RequestException:
                pass
            
            print(f"Attempt {attempt + 1}/{max_retries}: Fuseki not ready, waiting {delay}s...")
            time.sleep(delay)
        
        print("Fuseki failed to become available")
        return False
    
    def upload_rdf_graph(self, graph: Graph, graph_name: Optional[str] = None) -> bool:
        """Upload an RDF graph to Fuseki."""
        try:
            # Serialize graph to turtle format
            turtle_data = graph.serialize(format="turtle")
            
            # Create basic auth header manually
            credentials = base64.b64encode(b"admin:admin_password").decode('ascii')
            headers = {
                "Content-Type": "text/turtle; charset=utf-8",
                "Authorization": f"Basic {credentials}"
            }
            
            # If graph_name is provided, use named graph
            params = {}
            if graph_name:
                params["graph"] = graph_name
            
            response = requests.post(
                self.upload_url,
                data=turtle_data,
                headers=headers,
                params=params,
                timeout=30
            )
            
            if response.status_code in [200, 201, 204]:
                graph_info = f" to graph '{graph_name}'" if graph_name else ""
                print(f"Successfully uploaded RDF data to Fuseki{graph_info}")
                return True
            else:
                print(f"Failed to upload RDF data. Status: {response.status_code}, Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"Error uploading RDF data to Fuseki: {e}")
            return False
    
    def upload_ttl_file(self, ttl_file_path: str, graph_name: Optional[str] = None) -> bool:
        """Upload a TTL file directly to Fuseki."""
        try:
            with open(ttl_file_path, 'r', encoding='utf-8') as f:
                turtle_data = f.read()
            
            # Create basic auth header manually
            credentials = base64.b64encode(b"admin:admin_password").decode('ascii')
            headers = {
                "Content-Type": "text/turtle; charset=utf-8",
                "Authorization": f"Basic {credentials}"
            }
            
            params = {}
            if graph_name:
                params["graph"] = graph_name
            
            response = requests.post(
                self.upload_url,
                data=turtle_data,
                headers=headers,
                params=params,
                timeout=30
            )
            
            if response.status_code in [200, 201, 204]:
                graph_info = f" to graph '{graph_name}'" if graph_name else ""
                print(f"Successfully uploaded {ttl_file_path} to Fuseki{graph_info}")
                return True
            else:
                print(f"Failed to upload {ttl_file_path}. Status: {response.status_code}, Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"Error uploading TTL file to Fuseki: {e}")
            return False
    
    def query_count_triples(self) -> int:
        """Query the total number of triples in the dataset."""
        try:
            query = "SELECT (COUNT(*) AS ?count) WHERE { ?s ?p ?o }"
            response = requests.post(
                self.query_url,
                data={"query": query},
                headers={"Accept": "application/sparql-results+json"},
                timeout=10
            )
            
            if response.status_code == 200:
                results = response.json()
                count = int(results["results"]["bindings"][0]["count"]["value"])
                return count
            else:
                print(f"Failed to query triple count. Status: {response.status_code}")
                return -1
                
        except Exception as e:
            print(f"Error querying triple count: {e}")
            return -1
        
    def query(self, sparql_query: str, accept_header: str = "application/sparql-results+json"):
        """Execute a SPARQL query and return results."""
        try:
            response = requests.post(
                self.query_url,
                data={"query": sparql_query},
                headers={"Accept": accept_header},
                timeout=30
            )
            
            if response.status_code == 200:
                if accept_header == "application/sparql-results+json":
                    return response.json()
                else:
                    return response.text
            else:
                raise Exception(f"Query failed with status {response.status_code}: {response.text}")
                
        except Exception as e:
            raise Exception(f"Error executing SPARQL query: {e}")
    
    def clear_dataset(self):
        """Clear all data from the dataset."""
        try:
            # Use SPARQL UPDATE to clear all triples
            clear_query = "CLEAR ALL"
            
            # Create basic auth header manually
            credentials = base64.b64encode(b"admin:admin_password").decode('ascii')
            headers = {
                "Content-Type": "application/sparql-update",
                "Authorization": f"Basic {credentials}"
            }
            
            # Use the update endpoint
            update_url = f"{self.fuseki_url}/{self.dataset}/update"
            
            response = requests.post(
                update_url,
                data=clear_query,
                headers=headers,
                timeout=30
            )
            
            if response.status_code in [200, 204]:
                print("Successfully cleared all data from the dataset")
                return True
            else:
                raise Exception(f"Failed to clear dataset. Status: {response.status_code}, Response: {response.text}")
                
        except Exception as e:
            raise Exception(f"Error clearing dataset: {e}")
