"""
Enhanced Knowledge Graph Service with comprehensive monitoring, health checks, and error handling.
"""

import time
import logging
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from rdflib import Graph, URIRef, Literal
from collections import defaultdict, deque
import threading

from fuseki_client import FusekiClient
from file_watcher import FileWatcherService
from utils import create_rdf_graph_from_papers

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KGService:
    """Enhanced Knowledge Graph Service with monitoring and health checks."""
    
    def __init__(self, fuseki_url: str = "http://fuseki:3030", dataset_name: str = "matic_papers_kg"):
        self.fuseki_url = fuseki_url
        self.dataset_name = dataset_name
        self.fuseki_client = FusekiClient(fuseki_url, dataset_name)
        
        # Monitoring and metrics
        self.start_time = time.time()
        self.metrics = {
            "operations_count": 0,
            "successful_operations": 0,
            "failed_operations": 0,
            "total_triples_added": 0,
            "last_operation_time": None,
            "average_operation_time": 0.0
        }
        
        # Error tracking
        self.recent_errors = deque(maxlen=100)  # Keep last 100 errors
        self.operation_times = deque(maxlen=50)  # Keep last 50 operation times
        
        # Health status
        self.last_health_check = None
        self.health_status = "unknown"
        
        # File watcher (will be initialized externally)
        self.file_watcher = None
        
        # Thread safety
        self.lock = threading.Lock()
        
        logger.info(f"KGService initialized with Fuseki at {fuseki_url}")
    
    def test_fuseki_connection(self) -> bool:
        """Test connection to Fuseki server."""
        try:
            # Use the simpler count query instead of a generic query
            count = self.fuseki_client.query_count_triples()
            self.health_status = "healthy"
            self.last_health_check = datetime.now()
            return count >= 0
        except Exception as e:
            logger.error(f"Fuseki connection test failed: {e}")
            self.health_status = "unhealthy"
            self.last_health_check = datetime.now()
            self._record_error(f"Fuseki connection failed: {str(e)}")
            return False
    
    def get_graph_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics about the knowledge graph."""
        start_time = time.time()
        
        try:
            # Use the existing query_count_triples method for simplicity
            total_triples = self.fuseki_client.query_count_triples()
            
            # For a basic implementation, return simple stats
            # Could be enhanced later with more detailed queries
            stats = {
                "total_triples": total_triples,
                "query_time_seconds": time.time() - start_time,
                "last_updated": datetime.now().isoformat(),
                "status": "available" if total_triples >= 0 else "error"
            }
            
            logger.info(f"Graph statistics retrieved: {total_triples} triples")
            return stats
                
        except Exception as e:
            error_msg = f"Failed to get graph statistics: {str(e)}"
            logger.error(error_msg)
            self._record_error(error_msg)
            raise
    
    def add_graph(self, rdf_graph: Graph) -> int:
        """Add an RDF graph to the knowledge base with validation and monitoring."""
        start_time = time.time()
        
        try:
            with self.lock:
                self.metrics["operations_count"] += 1
                
                # Validate the graph
                if not self._validate_graph(rdf_graph):
                    raise ValueError("Graph validation failed")
                
                # Count triples before adding
                initial_count = len(rdf_graph)
                
                # Remove duplicates if any
                unique_triples = self._remove_duplicates(rdf_graph)
                unique_count = len(unique_triples)
                
                if unique_count < initial_count:
                    logger.info(f"Removed {initial_count - unique_count} duplicate triples")                # Add to Fuseki
                success = self.fuseki_client.upload_rdf_graph(unique_triples)
                if not success:
                    raise Exception("Failed to upload RDF graph to Fuseki")
                
                # Update metrics
                processing_time = time.time() - start_time
                self.metrics["successful_operations"] += 1
                self.metrics["total_triples_added"] += unique_count
                self.metrics["last_operation_time"] = datetime.now().isoformat()
                
                # Update average operation time
                self.operation_times.append(processing_time)
                self.metrics["average_operation_time"] = sum(self.operation_times) / len(self.operation_times)
                
                logger.info(f"Successfully added {unique_count} triples in {processing_time:.2f}s")
                return unique_count
                
        except Exception as e:
            self.metrics["failed_operations"] += 1
            error_msg = f"Failed to add graph: {str(e)}"
            logger.error(error_msg)
            self._record_error(error_msg)
            raise
    
    def _validate_graph(self, rdf_graph: Graph) -> bool:
        """Validate RDF graph for common issues."""
        try:
            # Check if graph is not empty
            if len(rdf_graph) == 0:
                logger.warning("Empty graph provided")
                return True  # Empty graph is technically valid
            
            # Check for malformed triples
            for subject, predicate, obj in rdf_graph:
                if not subject or not predicate:
                    logger.error(f"Invalid triple: {subject} {predicate} {obj}")
                    return False
            
            # Additional validation could be added here
            logger.debug(f"Graph validation passed for {len(rdf_graph)} triples")
            return True
            
        except Exception as e:
            logger.error(f"Graph validation error: {e}")
            return False
    
    def _remove_duplicates(self, rdf_graph: Graph) -> Graph:
        """Remove duplicate triples from the graph."""
        try:
            # Create a new graph (Graph automatically handles duplicates)
            unique_graph = Graph()
            
            # Copy all triples (duplicates will be automatically filtered)
            for triple in rdf_graph:
                unique_graph.add(triple)
            
            return unique_graph
            
        except Exception as e:
            logger.error(f"Error removing duplicates: {e}")
            return rdf_graph  # Return original graph if deduplication fails
    
    def clear_graph(self):
        """Clear all data from the knowledge graph."""
        try:
            with self.lock:
                self.fuseki_client.clear_dataset()
                logger.info("Knowledge graph cleared successfully")
                
                # Reset some metrics
                self.metrics["total_triples_added"] = 0
                
        except Exception as e:
            error_msg = f"Failed to clear graph: {str(e)}"
            logger.error(error_msg)
            self._record_error(error_msg)
            raise
    def create_backup(self) -> str:
        """Create a backup of the current knowledge graph."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"kg_backup_{timestamp}.ttl"
            backup_path = f"/app/data/backups/{backup_filename}"
            
            # Ensure backup directory exists
            os.makedirs(os.path.dirname(backup_path), exist_ok=True)
            
            # Query all triples
            query = "SELECT * WHERE { ?s ?p ?o }"
            result = self.fuseki_client.query(query)
            
            # Create backup graph
            backup_graph = Graph()
              # Parse the SPARQL JSON response
            if "results" in result and "bindings" in result["results"]:
                for binding in result["results"]["bindings"]:
                    # Convert string values to RDF terms
                    s_value = binding['s']['value']
                    s_type = binding['s']['type']
                    if s_type == 'uri':
                        s = URIRef(s_value)
                    else:
                        s = Literal(s_value)
                    
                    p_value = binding['p']['value'] 
                    p_type = binding['p']['type']
                    if p_type == 'uri':
                        p = URIRef(p_value)
                    else:
                        p = Literal(p_value)
                    
                    o_value = binding['o']['value']
                    o_type = binding['o']['type']
                    if o_type == 'uri':
                        o = URIRef(o_value)
                    else:
                        o = Literal(o_value)
                    
                    backup_graph.add((s, p, o))
            
            # Serialize to file
            backup_graph.serialize(destination=backup_path, format='turtle')
            
            logger.info(f"Backup created: {backup_path}")
            return backup_path
            
        except Exception as e:
            error_msg = f"Failed to create backup: {str(e)}"
            logger.error(error_msg)
            self._record_error(error_msg)
            raise
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current service metrics."""
        uptime = time.time() - self.start_time
        
        return {
            **self.metrics,
            "uptime_seconds": uptime,
            "health_status": self.health_status,
            "last_health_check": self.last_health_check.isoformat() if self.last_health_check else None,
            "recent_errors_count": len(self.recent_errors),
            "file_watcher_active": self.file_watcher is not None
        }
    
    def get_recent_errors(self) -> List[str]:
        """Get list of recent errors."""
        return list(self.recent_errors)
    
    def _record_error(self, error_msg: str):
        """Record an error with timestamp."""
        timestamped_error = f"{datetime.now().isoformat()}: {error_msg}"
        self.recent_errors.append(timestamped_error)
        logger.error(timestamped_error)
    
    def set_file_watcher(self, file_watcher: FileWatcherService):
        """Set the file watcher service."""
        self.file_watcher = file_watcher
        logger.info("File watcher service attached")
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status."""
        # Perform fresh health check
        fuseki_healthy = self.test_fuseki_connection()
        
        return {
            "status": "healthy" if fuseki_healthy else "unhealthy",
            "fuseki_connection": fuseki_healthy,
            "uptime_seconds": time.time() - self.start_time,
            "last_check": datetime.now().isoformat(),
            "metrics": self.get_metrics(),
            "recent_errors": list(self.recent_errors)[-5:]  # Last 5 errors
        }
