# ExtremeXP - Matic PapersWithCode KG Builder

This project parses JSON data about scientific papers (sourced from PapersWithCode via Matic)
and transforms it into an RDF knowledge graph. It uses Docker and Docker Compose for
easy management and deployment with an Apache Jena Fuseki triplestore.

## Prerequisites

- Docker (https://www.docker.com/get-started)
- Docker Compose (usually comes with Docker Desktop)

## Project Structure

extremexp_kg_matic/
├── data/
│ ├── matic_input_01.json
│ └── output.ttl
├── src/
│ ├── main.py
│ ├── kg_schema.py
│ └── utils.py
├── sparql_queries/
│ └── ...
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md

## Setup

1.  **Place Input Data:**
    Ensure your input JSON file from Matic is placed in the `data/` directory (e.g., `data/matic_input_01.json`). The `src/main.py` script is configured to read from this location.

2.  **Build and Run with Docker Compose:**
    Open your terminal in the project root directory (`extremexp_kg_matic/`) and run:
    ```bash
    docker-compose up --build
    ```
    This will:
    - Build the `parser` Docker image.
    - Start the `parser` service, which will execute `src/main.py`. This script reads `data/matic_input_01.json` and generates `data/output.ttl`.
    - Start the `fuseki` service (Apache Jena Fuseki triplestore).

## Interacting with the Knowledge Graph

1.  **Parser Output:**
    After the `parser` service completes (you'll see its logs in the `docker-compose up` output), the generated RDF triples will be in `data/output.ttl`.

2.  **Access Fuseki:**
    Open your web browser and go to `http://localhost:3030`. This is the Fuseki UI.

3.  **Create/Manage Dataset in Fuseki (if not auto-created):**
    - If a dataset named `matic_papers_kg` (or `/ds`) isn't already listed, you might need to create it.
    - Click on "manage datasets" -> "add new dataset".
    - Dataset name: `matic_papers_kg` (or any name you prefer).
    - Dataset type: `TDB2 (persistent)`.
    - Click "create dataset".

4.  **Upload RDF Data to Fuseki:**
    - Select your dataset (e.g., `matic_papers_kg`) from the list.
    - Go to the "upload data" tab.
    - Click "select files" and navigate to the `data/output.ttl` file on your host machine. (Fuseki running in Docker can access files you explicitly mount or you can upload from your host).
    - Click "upload all".

5.  **Query Data:**
    - Select your dataset.
    - Go to the "query" tab.
    - You can write SPARQL queries directly or upload `.rq` files from the `sparql_queries/` directory.
    - Example:
      ```sparql
      PREFIX ex: <http://extremexp.eu/ontology/matic_papers/>
      PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

      SELECT ?s ?p ?o WHERE {
        ?s ?p ?o .
      } LIMIT 100
      ```

## Development

-   To re-run the parser after code changes:
    ```bash
    docker-compose build parser
    docker-compose up parser
    ```
    (You might need to stop existing containers with `docker-compose down` first if there are conflicts or you want a clean start for Fuseki).
-   To stop all services:
    ```bash
    docker-compose down
    ```
-   To remove persistent Fuseki data (if you want to start fresh):
    Delete the `fuseki_data/` directory on your host (while containers are down).

## Notes on Fuseki Command in `docker-compose.yml`

The command `/jena-fuseki/fuseki-server --loc /fuseki/matic_papers_kg /ds` in the `docker-compose.yml` tells Fuseki to use `/fuseki/matic_papers_kg` as the persistent location for a dataset that will be available at the `/ds` endpoint (e.g., `http://localhost:3030/ds`).
You can also manage datasets entirely through the UI. The file `/staging/output.ttl` is available inside the Fuseki container if you want to use Fuseki's UI to upload data from within its own filesystem space.
