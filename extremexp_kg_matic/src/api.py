"""
FastAPI server for Knowledge Graph service with health monitoring and management endpoints.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import json
import time
import logging
import traceback
from datetime import datetime
from contextlib import asynccontextmanager

from kg_service import KGService
from utils import create_rdf_graph_from_papers
from file_watcher import FileWatcherService
from monitoring import system_logger, metrics_collector

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global file watcher variable
file_watcher_service = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    global file_watcher_service
    
    # Startup
    try:
        logger.info("Starting file watcher service...")
          # Initialize file watcher with data directory
        data_dir = "/app/data"
        file_watcher_service = FileWatcherService(
            data_dir=data_dir,
            kg_service=kg_service,
            rdf_processor=create_rdf_graph_from_papers
        )
        
        # Attach file watcher to kg_service
        kg_service.set_file_watcher(file_watcher_service)
        
        # Process existing files first
        existing_files = file_watcher_service.process_existing_files()
        logger.info(f"Processed {len(existing_files)} existing files on startup")
        
        # Start watching for new files
        file_watcher_service.start()
        logger.info("File watcher service started successfully")
        
    except Exception as e:
        logger.error(f"Failed to start file watcher service: {e}")
        logger.error(traceback.format_exc())
    
    yield
    
    # Shutdown
    try:
        if file_watcher_service:
            logger.info("Stopping file watcher service...")
            file_watcher_service.stop()
            logger.info("File watcher service stopped")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")

# Initialize FastAPI app with lifespan
app = FastAPI(
    title="Knowledge Graph API",
    description="API for managing and monitoring knowledge graphs",
    version="1.0.0",
    lifespan=lifespan
)

# Middleware for request logging and metrics
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all API requests with timing and metrics."""
    start_time = time.time()
    client_ip = request.client.host if request.client else "unknown"
    
    # Process request
    response = await call_next(request)
    
    # Calculate response time
    response_time = time.time() - start_time
    
    # Log request with structured logging
    system_logger.log_api_request(
        endpoint=str(request.url.path),
        method=request.method,
        status_code=response.status_code,
        response_time=response_time,
        client_ip=client_ip
    )
    
    # Update metrics
    metrics_collector.increment_counter("api_requests_total")
    metrics_collector.increment_counter(f"api_requests_{response.status_code}")
    metrics_collector.record_timing("api_response_time", response_time)
    
    if response.status_code >= 400:
        metrics_collector.increment_counter("api_errors")
    
    return response

# Initialize KG Service
kg_service = KGService()

# Pydantic models for request/response
class PaperData(BaseModel):
    title: str
    year: Optional[int] = None
    pdfUrl: Optional[str] = None
    url: Optional[str] = None  # Alternative field name for PDF URL
    papersWithCodeUrl: Optional[str] = None
    origin: Optional[str] = None  # Alternative field name for Papers with Code URL
    mentions: Optional[Dict] = {}
    
    # Additional fields commonly found in paper data
    tasks: Optional[List[str]] = []
    datasets: Optional[List[str]] = []
    methods: Optional[List[str]] = []
    results: Optional[List[Dict]] = []

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    uptime_seconds: float

class DetailedHealthResponse(BaseModel):
    status: str
    timestamp: str
    uptime_seconds: float
    fuseki_status: str
    graph_stats: Dict[str, Any]
    file_watcher_status: str
    recent_errors: List[str]
    metrics: Dict[str, Any]

class ProcessResponse(BaseModel):
    success: bool
    message: str
    triples_added: Optional[int] = None
    processing_time: Optional[float] = None

# Global variables for tracking
start_time = time.time()
recent_errors: List[str] = []

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Knowledge Graph API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "detailed_health": "/health/detailed",
            "process_papers": "/process/papers",
            "upload_file": "/upload",
            "stats": "/stats",
            "metrics": "/metrics",
            "backup": "/backup",
            "graph_clear": "/graph",
            "scan_files": "/scan-files"
        }
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Basic health check endpoint."""
    try:
        uptime = time.time() - start_time
        return HealthResponse(
            status="healthy",
            timestamp=datetime.now().isoformat(),
            uptime_seconds=uptime
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")

@app.get("/health/detailed", response_model=DetailedHealthResponse)
async def detailed_health_check():
    """Comprehensive health check with system status."""
    try:
        uptime = time.time() - start_time
        
        # Check Fuseki connection
        fuseki_status = "healthy" if kg_service.test_fuseki_connection() else "unhealthy"
        
        # Get graph statistics
        try:
            graph_stats = kg_service.get_graph_statistics()
        except Exception as e:
            graph_stats = {"error": str(e)}
          # Check file watcher status
        file_watcher_status = "active" if hasattr(kg_service, 'file_watcher') and kg_service.file_watcher else "inactive"
          # Get enhanced metrics from monitoring system
        monitoring_metrics = metrics_collector.get_metrics_summary()
        
        # Combine with existing metrics (monitoring metrics take precedence)
        combined_metrics = monitoring_metrics.copy()
        kg_metrics_basic = kg_service.get_metrics() if hasattr(kg_service, 'get_metrics') else {}
        combined_metrics.update(kg_metrics_basic)
        return DetailedHealthResponse(
            status="healthy" if fuseki_status == "healthy" else "degraded",
            timestamp=datetime.now().isoformat(),
            uptime_seconds=uptime,
            fuseki_status=fuseki_status,
            graph_stats=graph_stats,
            file_watcher_status=file_watcher_status,
            recent_errors=recent_errors[-10:],  # Last 10 errors
            metrics=combined_metrics
        )
    except Exception as e:
        logger.error(f"Detailed health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Health check failed: {str(e)}")

@app.post("/process/papers", response_model=ProcessResponse)
async def process_papers(papers: List[PaperData]):
    """Process a list of papers and add them to the knowledge graph."""
    start_time_process = time.time()
    
    try:
        system_logger.log_event("info", "api_process_papers", 
                               f"Processing {len(papers)} papers via API")
        metrics_collector.increment_counter("papers_processed_api", len(papers))
          # Convert Pydantic models to dict
        papers_data = [paper.dict() for paper in papers]
        
        # Normalize field names to match what the RDF processor expects
        for paper in papers_data:
            # Handle URL field mapping - prioritize 'url' over 'pdfUrl'
            if paper.get('url') and not paper.get('pdfUrl'):
                paper['pdfUrl'] = paper['url']
            elif paper.get('pdfUrl') and not paper.get('url'):
                paper['url'] = paper['pdfUrl']
            
            # Handle Papers with Code URL mapping
            if paper.get('origin') and not paper.get('papersWithCodeUrl'):
                paper['papersWithCodeUrl'] = paper['origin']
            elif paper.get('papersWithCodeUrl') and not paper.get('origin'):
                paper['origin'] = paper['papersWithCodeUrl']
        
        # Create RDF graph from papers
        rdf_graph = create_rdf_graph_from_papers(papers_data)
        
        # Add to knowledge graph
        triples_added = kg_service.add_graph(rdf_graph)
        
        processing_time = time.time() - start_time_process
        
        system_logger.log_event("info", "api_process_success", 
                               f"Successfully processed {len(papers)} papers", 
                               {"triples_added": triples_added, "processing_time": processing_time})
        
        metrics_collector.increment_counter("triples_added_api", triples_added)
        metrics_collector.record_timing("api_processing_time", processing_time)
        
        logger.info(f"Successfully processed {len(papers)} papers, added {triples_added} triples")
        
        return ProcessResponse(
            success=True,
            message=f"Successfully processed {len(papers)} papers",
            triples_added=triples_added,
            processing_time=processing_time
        )
        
    except Exception as e:
        error_msg = f"Failed to process papers: {str(e)}"
        processing_time = time.time() - start_time_process
        
        system_logger.log_event("error", "api_process_failed", error_msg, 
                               {"processing_time": processing_time, "paper_count": len(papers)})
        metrics_collector.increment_counter("api_processing_errors")
        
        logger.error(error_msg)
        recent_errors.append(f"{datetime.now().isoformat()}: {error_msg}")
        
        raise HTTPException(status_code=500, detail=error_msg)

@app.post("/upload", response_model=ProcessResponse)
async def upload_file(file: UploadFile = File(...)):
    """Upload and process a JSON file containing papers data."""
    start_time_process = time.time()
    
    try:
        system_logger.log_event("info", "api_file_upload", 
                               f"File upload started: {file.filename}")
        metrics_collector.increment_counter("files_uploaded_api")
        
        # Validate file type
        if not file.filename.endswith('.json'):
            error_msg = "Only JSON files are supported"
            system_logger.log_event("error", "api_upload_invalid_type", error_msg, 
                                   {"filename": file.filename})
            raise HTTPException(status_code=400, detail=error_msg)
        
        # Read and parse JSON content
        content = await file.read()
        system_logger.log_event("info", "api_upload_file_read", 
                               f"File read: {file.filename}", {"size_bytes": len(content)})
        
        # Check if content is empty
        if not content:
            error_msg = "Uploaded file is empty"
            system_logger.log_event("error", "api_upload_empty", error_msg, 
                                   {"filename": file.filename})
            raise HTTPException(status_code=400, detail=error_msg)
        
        try:
            content_str = content.decode('utf-8')
            logger.info(f"Decoded content preview: {content_str[:100]}...")
        except UnicodeDecodeError as e:
            error_msg = f"File encoding error: {str(e)}"
            system_logger.log_event("error", "api_upload_encoding_error", error_msg, 
                                   {"filename": file.filename})
            logger.error(f"Unicode decode error: {e}")
            raise HTTPException(status_code=400, detail=error_msg)
        
        papers_data = json.loads(content_str)
        
        # Ensure it's a list
        if not isinstance(papers_data, list):
            papers_data = [papers_data]
        
        system_logger.log_event("info", "api_upload_parsed", 
                               f"JSON parsed successfully", 
                               {"filename": file.filename, "paper_count": len(papers_data)})
        
        # Create RDF graph from papers
        rdf_graph = create_rdf_graph_from_papers(papers_data)
        
        # Add to knowledge graph
        triples_added = kg_service.add_graph(rdf_graph)
        
        processing_time = time.time() - start_time_process
        
        system_logger.log_event("info", "api_upload_success", 
                               f"File upload processed successfully", 
                               {"filename": file.filename, "triples_added": triples_added, 
                                "processing_time": processing_time})
        
        metrics_collector.increment_counter("triples_added_upload", triples_added)
        metrics_collector.record_timing("api_upload_time", processing_time)
        
        logger.info(f"Successfully processed uploaded file {file.filename}, added {triples_added} triples")
        
        return ProcessResponse(
            success=True,
            message=f"Successfully processed file {file.filename}",
            triples_added=triples_added,
            processing_time=processing_time
        )
    except json.JSONDecodeError as e:
        error_msg = f"Invalid JSON in uploaded file: {str(e)}"
        processing_time = time.time() - start_time_process
        
        system_logger.log_event("error", "api_upload_json_error", error_msg, 
                               {"filename": file.filename, "processing_time": processing_time})
        metrics_collector.increment_counter("api_upload_json_errors")
        
        logger.error(error_msg)
        raise HTTPException(status_code=400, detail=error_msg)
    
    except Exception as e:
        error_msg = f"Failed to process uploaded file: {str(e)}"
        processing_time = time.time() - start_time_process
        
        system_logger.log_event("error", "api_upload_failed", error_msg, 
                               {"filename": file.filename, "processing_time": processing_time})
        metrics_collector.increment_counter("api_upload_errors")
        
        logger.error(error_msg)
        recent_errors.append(f"{datetime.now().isoformat()}: {error_msg}")
        
        raise HTTPException(status_code=500, detail=error_msg)

@app.get("/stats")
async def get_stats():
    """Get knowledge graph statistics."""
    try:
        system_logger.log_event("info", "api_stats_request", "Statistics requested")
        
        stats = kg_service.get_graph_statistics()
        return JSONResponse(content=stats)
    except Exception as e:
        error_msg = f"Failed to get statistics: {str(e)}"
        system_logger.log_event("error", "api_stats_failed", error_msg)
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@app.get("/metrics")
async def get_metrics():
    """Get detailed system metrics and monitoring data."""
    try:
        system_logger.log_event("info", "api_metrics_request", "Metrics requested")
        
        # Get comprehensive metrics
        monitoring_metrics = metrics_collector.get_metrics_summary()
        kg_metrics = kg_service.get_graph_statistics() if hasattr(kg_service, 'get_graph_statistics') else {}
        
        # Get file watcher status if available
        file_watcher_metrics = {}
        if file_watcher_service:
            file_watcher_metrics = file_watcher_service.get_status()
        
        combined_metrics = {
            "timestamp": datetime.now().isoformat(),
            "system_metrics": monitoring_metrics,
            "knowledge_graph": kg_metrics,
            "file_watcher": file_watcher_metrics,
            "recent_errors": recent_errors[-10:]  # Last 10 errors
        }
        
        return JSONResponse(content=combined_metrics)
        
    except Exception as e:
        error_msg = f"Failed to get metrics: {str(e)}"
        system_logger.log_event("error", "api_metrics_failed", error_msg)
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@app.post("/backup")
async def create_backup(background_tasks: BackgroundTasks):
    """Create a backup of the knowledge graph."""
    try:
        def backup_task():
            try:
                backup_path = kg_service.create_backup()
                logger.info(f"Backup created successfully: {backup_path}")
            except Exception as e:
                logger.error(f"Backup failed: {e}")
                recent_errors.append(f"{datetime.now().isoformat()}: Backup failed: {str(e)}")
        
        background_tasks.add_task(backup_task)
        
        return {"message": "Backup started in background"}
        
    except Exception as e:
        error_msg = f"Failed to start backup: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@app.delete("/graph")
async def clear_graph():
    """Clear all data from the knowledge graph."""
    try:
        kg_service.clear_graph()
        logger.info("Knowledge graph cleared successfully")
        return {"message": "Knowledge graph cleared successfully"}
    except Exception as e:
        error_msg = f"Failed to clear graph: {str(e)}"
        logger.error(error_msg)
        recent_errors.append(f"{datetime.now().isoformat()}: {error_msg}")
        raise HTTPException(status_code=500, detail=error_msg)

@app.post("/scan-files")
async def scan_files():
    """Manually scan and process new files in the data directory."""
    try:
        if file_watcher_service:
            processed_files = file_watcher_service.process_existing_files()
            return {
                "message": f"Scanned and processed {len(processed_files)} files",
                "processed_files": processed_files,
                "success": True
            }
        else:
            raise HTTPException(status_code=500, detail="File watcher service not available")
    except Exception as e:
        error_msg = f"Failed to scan files: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unexpected errors."""
    error_msg = f"Unexpected error: {str(exc)}"
    logger.error(f"Global exception: {error_msg}\n{traceback.format_exc()}")
    recent_errors.append(f"{datetime.now().isoformat()}: {error_msg}")
    
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": error_msg}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
