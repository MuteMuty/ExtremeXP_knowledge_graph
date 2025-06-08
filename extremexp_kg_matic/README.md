# ExtremeXP Knowledge Graph Service

A comprehensive, production-ready knowledge graph generation system that processes scientific paper metadata and maintains a queryable RDF triplestore with advanced monitoring, automatic data processing, and full API management capabilities.

## 🚀 Key Features

### Core Functionality
- **Intelligent Data Processing**: Automatically processes scientific paper metadata with URL and year extraction from arXiv links
- **Dual Processing Modes**: Support for both API-driven processing and automatic file watching
- **Direct Fuseki Integration**: Seamless RDF data upload to Apache Jena Fuseki triplestore
- **Field Normalization**: Smart handling of different field naming conventions (`url`/`pdfUrl`, `origin`/`papersWithCodeUrl`)

### Advanced Monitoring & Health Checks
- **Comprehensive Health Monitoring**: Basic and detailed health endpoints with system status tracking
- **Structured Logging**: Enhanced logging with event categorization and structured data
- **Metrics Collection**: Real-time metrics for API requests, processing times, and system performance
- **Error Tracking**: Automatic error logging and recent error history

### Automation & File Management
- **Automatic File Watching**: Real-time monitoring and processing of new JSON files
- **Smart Backup System**: Automated TTL backup generation with timestamp-based naming
- **Batch Processing**: Efficient processing of multiple papers and large datasets
- **File Upload Support**: Direct file upload through REST API

### API Management
- **RESTful API**: Complete REST API with 9 endpoints for all operations
- **Request Logging**: Comprehensive API request tracking with timing and client information
- **Background Processing**: Asynchronous processing for backup and bulk operations
- **Error Handling**: Robust error handling with detailed error responses

## 🛠️ Quick Start

### Prerequisites
- Docker and Docker Compose
- Python 3.8+ (for testing and development)

### 1. System Startup
```powershell
# Start the complete system (Fuseki + Knowledge Graph Service)
docker-compose up -d

# View logs to monitor startup
docker-compose logs -f kg_service

# Check system health
curl http://localhost:8000/health
```

### 2. Verify Installation
```powershell
# Run comprehensive API tests to verify all functionality
python comprehensive_api_test.py

# Check detailed system status
curl http://localhost:8000/health/detailed

# View current knowledge graph statistics
curl http://localhost:8000/stats
```

### 3. Access Interfaces
- **REST API**: http://localhost:8000 (Main Knowledge Graph API)
- **Fuseki Interface**: http://localhost:3030 (Apache Jena Fuseki Web UI)
- **SPARQL Query Endpoint**: http://localhost:3030/matic_papers_kg/sparql
- **Graph Query Interface**: http://localhost:3030/#/dataset/matic_papers_kg/query

## 📚 Complete API Reference

The Knowledge Graph Service provides a comprehensive REST API with 9 endpoints for complete system management:

### Core Processing Endpoints

#### `POST /process/papers`
Process a list of papers directly through the API.
```json
{
  "papers": [
    {
      "url": "https://arxiv.org/pdf/2103.14030v2.pdf",
      "origin": "https://paperswithcode.com/paper/swin-transformer-hierarchical-vision",
      "title": "Swin Transformer: Hierarchical Vision Transformer using Shifted Windows",
      "tasks": ["Image Classification", "Instance Segmentation", ],
      "datasets": ["ImageNet", "MS COCO"],
      "results": [{
          "task": "Semantic Segmentation",
          "dataset": "ADE20K",
          "model": "Swin-L (UperNet, ImageNet-22k pretrain)",
          "metric": "Validation mIoU",
          "value": "53.50",
          "rank": "75"
      }],
      "methods": ["Adam", "Attention Dropout"]
    }
  ]
}
```

#### `POST /upload`
Upload and process JSON files containing paper metadata.
```powershell
# Upload a JSON file
curl -X POST -F "file=@papers.json" http://localhost:8000/upload
```

#### `POST /scan-files`
Manually trigger scanning and processing of files in the data directory.
```powershell
curl -X POST http://localhost:8000/scan-files
```

### Health & Monitoring Endpoints

#### `GET /health`
Basic health check with uptime information.
```json
{
  "status": "healthy",
  "timestamp": "2025-06-08T10:30:00",
  "uptime_seconds": 3600.5
}
```

#### `GET /health/detailed`
Comprehensive system health with component status.
```json
{
  "status": "healthy",
  "timestamp": "2025-06-08T10:30:00",
  "uptime_seconds": 3600.5,
  "fuseki_status": "healthy",
  "graph_stats": {"total_triples": 1500},
  "file_watcher_status": "active",
  "recent_errors": [],
  "metrics": {...}
}
```

#### `GET /stats`
Knowledge graph statistics and metrics.
```json
{
  "total_triples": 1500,
  "total_papers": 50,
  "papers_with_urls": 45,
  "papers_with_years": 48,
  "query_time_seconds": 0.023
}
```

#### `GET /metrics`
Detailed system metrics and performance data.
```json
{
  "timestamp": "2025-06-08T10:30:00",
  "system_metrics": {
    "uptime_seconds": 3600.5,
    "counters": {"api_requests_total": 127},
    "timings_summary": {"api_response_time": {"avg": 0.15}}
  },
  "knowledge_graph": {...},
  "file_watcher": {"status": "active", "files_processed": 12}
}
```

### Data Management Endpoints

#### `POST /backup`
Create a timestamped backup of the knowledge graph.
```powershell
curl -X POST http://localhost:8000/backup
```

#### `DELETE /graph`
Clear all data from the knowledge graph.
```powershell
curl -X DELETE http://localhost:8000/graph
```

### Root Endpoint
#### `GET /`
API information and endpoint discovery.
```json
{
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
```

## 🗂️ Project Structure

```
extremexp_kg_matic/
├── src/                          # Core application source code
│   ├── api.py                   # FastAPI server with all endpoints
│   ├── kg_service.py           # Knowledge Graph service with monitoring
│   ├── file_watcher.py         # Automatic file monitoring service
│   ├── fuseki_client.py        # Apache Jena Fuseki integration
│   ├── utils.py                # RDF processing and graph utilities
│   ├── monitoring.py           # Structured logging and metrics collection
│   ├── kg_schema.py           # RDF schema definitions
│   └── main.py                # Main application entry point
├── data/                        # Data directory (automatically monitored)
│   ├── *.json                  # Input JSON files (auto-processed)
│   ├── *.ttl                   # Generated TTL files
│   └── backups/                # Automatic backup storage
│       └── kg_backup_*.ttl     # Timestamped backups
├── fuseki_data/                # Persistent Fuseki data
│   ├── configuration/          # Fuseki dataset configurations
│   ├── databases/              # TDB2 database files
│   └── logs/                   # Fuseki server logs
├── sparql_queries/             # SPARQL query examples
│   └── *.rq                   # Sample queries for data exploration
├── test_data/                  # Test files and fixtures
├── docker-compose.yml          # Complete system orchestration
├── Dockerfile                  # Knowledge Graph service container
├── requirements.txt            # Python dependencies
├── comprehensive_api_test.py   # Complete API test suite
├── cleanup.py                  # Maintenance and cleanup utilities
└── README.md                   # This documentation
```

## 💾 Data Processing Features

### Intelligent Field Mapping
The system automatically handles different field naming conventions found in academic paper metadata:

- **URL Handling**: Accepts both `url` and `pdfUrl` fields
- **Source Mapping**: Maps both `origin` and `papersWithCodeUrl` fields
- **Year Extraction**: Automatically extracts publication years from arXiv URLs
- **Enhanced Metadata**: Supports `tasks`, `datasets`, `methods`, and `results` arrays

### Automatic File Processing
- **Startup Processing**: All existing JSON files are processed on system startup
- **Real-time Monitoring**: New files are automatically detected and processed
- **Error Resilience**: Failed files are logged but don't stop the system
- **Progress Tracking**: Detailed logging of all processing activities

### Data Validation
- **JSON Schema Validation**: Ensures data integrity before processing
- **Field Normalization**: Standardizes field names across different data sources
- **Duplicate Handling**: Intelligent handling of duplicate papers and data
- **Error Recovery**: Graceful handling of malformed or incomplete data

## 🔧 System Architecture

### Multi-Container Deployment
- **Knowledge Graph Service** (Port 8000): FastAPI application with file monitoring
- **Apache Jena Fuseki** (Port 3030): RDF triplestore with SPARQL endpoint
- **Persistent Storage**: Shared volumes for data persistence and backup

### Processing Pipeline
1. **Data Ingestion**: JSON files → Field normalization → Validation
2. **RDF Generation**: Structured data → RDF triples → Graph creation
3. **Storage**: RDF graph → Fuseki triplestore → Persistent storage
4. **Monitoring**: All operations → Structured logging → Metrics collection

### Advanced Monitoring System
- **Structured Logging**: Categorized events with contextual data
- **Metrics Collection**: Performance tracking with timing summaries
- **Health Monitoring**: Component-level health checks
- **Error Tracking**: Automatic error detection and history

## 🚀 Setup & Installation

### Development Setup
1. **Clone and navigate to the project**:
   ```powershell
   cd FOG\extremexp_kg_matic
   ```

2. **Start the complete system**:
   ```powershell
   docker-compose up --build -d
   ```

3. **Verify system health**:
   ```powershell
   # Wait for services to start (30-60 seconds)
   Start-Sleep 60
   
   # Check system status
   Invoke-RestMethod -Uri "http://localhost:8000/health/detailed"
   ```

### Production Deployment
1. **Configure environment variables**:
   ```powershell
   # Set secure admin password current credentials(admin : admin_password)
   $env:ADMIN_PASSWORD = "your-secure-password"
   ```

2. **Start with production settings**:
   ```powershell
   docker-compose up -d
   ```

3. **Enable monitoring**:
   ```powershell
   # Set up log monitoring
   docker-compose logs -f kg_service
   ```

## 🔍 Querying the Knowledge Graph

### SPARQL Query Interface
Access the interactive SPARQL query interface at:
http://localhost:3030/#/dataset/matic_papers_kg/query

## 📁 Data Management

### Adding New Data
1. **Automatic Processing**: Simply copy JSON files to the `data/` directory
   ```powershell
   Copy-Item "new_papers.json" "data/"
   # File will be automatically processed within seconds
   ```

2. **API Upload**: Use the upload endpoint
   ```powershell
   curl -X POST -F "file=@papers.json" http://localhost:8000/upload
   ```

3. **Direct API Processing**: Send data directly
   ```powershell
   Invoke-RestMethod -Uri "http://localhost:8000/process/papers" -Method POST -Body ($papers | ConvertTo-Json) -ContentType "application/json"
   ```

### Backup Management
```powershell
# Create manual backup
Invoke-RestMethod -Uri "http://localhost:8000/backup" -Method POST

# List existing backups
Get-ChildItem "data/backups/" -Name "*.ttl"

# Automatic backups are created during processing
```

### Data Cleanup
```powershell
# Clear all data (use with caution!)
Invoke-RestMethod -Uri "http://localhost:8000/graph" -Method DELETE

# Run maintenance cleanup
python cleanup.py
```

## 🔧 Development & Maintenance

### Development Workflow
```powershell
# Rebuild after code changes
docker-compose down
docker-compose up --build -d

# View real-time logs
docker-compose logs -f kg_service

# Monitor specific components
docker-compose logs -f fuseki
```

### Testing & Validation
```powershell
# Run comprehensive API test suite
python comprehensive_api_test.py

# Check system metrics
Invoke-RestMethod -Uri "http://localhost:8000/metrics"
```

### Automated Cleanup
```powershell
# Run maintenance script
python cleanup.py
```

**Cleanup script automatically:**
- Removes old test results (7+ days)
- Maintains backup file retention (5 most recent)
- Cleans temporary files and directories
- Optimizes system performance

### System Health Monitoring
```powershell
# Basic health check
Invoke-RestMethod -Uri "http://localhost:8000/health"

# Detailed system status with component health
Invoke-RestMethod -Uri "http://localhost:8000/health/detailed"

# Comprehensive metrics and performance data
Invoke-RestMethod -Uri "http://localhost:8000/metrics"

# Knowledge graph statistics
Invoke-RestMethod -Uri "http://localhost:8000/stats"
```

### Troubleshooting

#### Common Issues
1. **Service won't start**: Check Docker Desktop is running
2. **API timeout**: Wait 60 seconds for services to fully initialize
3. **File not processed**: Check file format and permissions
4. **Query fails**: Verify Fuseki dataset exists

#### Debug Commands
```powershell
# Check container status
docker-compose ps

# View detailed logs
docker-compose logs kg_service --tail=50
docker-compose logs fuseki --tail=50

# Test Fuseki connection
Invoke-RestMethod -Uri "http://localhost:3030/$/ping"

# Reset everything (nuclear option)
docker-compose down -v
Remove-Item "fuseki_data" -Recurse -Force
docker-compose up --build -d
```

**Technologies Used:**
- FastAPI for REST API development
- Apache Jena Fuseki for RDF storage and SPARQL
- Docker & Docker Compose for containerization
- RDFLib for RDF graph processing
- Watchdog for file system monitoring