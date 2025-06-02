"""
File watcher service that monitors the data directory for new JSON files
and automatically processes them into the knowledge graph.
"""
import os
import time
import json
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from typing import List

from utils import create_rdf_graph_from_text
from fuseki_client import FusekiClient

class JSONFileHandler(FileSystemEventHandler):
    def __init__(self, fuseki_client: FusekiClient, data_dir: str, rdf_processor=None):
        self.fuseki_client = fuseki_client
        self.data_dir = data_dir
        self.processed_files = set()
        self.rdf_processor = rdf_processor
        
    def on_created(self, event):
        """Handle file creation events."""
        if not event.is_directory and event.src_path.endswith('.json'):
            print(f"New JSON file detected: {event.src_path}")
            # Add a small delay to ensure file write is complete
            time.sleep(2)
            self.process_json_file(event.src_path)
    
    def on_modified(self, event):
        """Handle file modification events."""
        if not event.is_directory and event.src_path.endswith('.json'):
            # Only process if we haven't processed this file recently
            if event.src_path not in self.processed_files:
                print(f"Modified JSON file detected: {event.src_path}")
                time.sleep(2)  # Wait for write completion
                self.process_json_file(event.src_path)
    
    def process_json_file(self, file_path: str) -> bool:
        """Process a single JSON file and upload to Fuseki."""
        try:
            print(f"Processing JSON file: {file_path}")
            
            # Load and validate JSON
            with open(file_path, 'r', encoding='utf-8') as f:
                papers_data = json.load(f)
            
            if not isinstance(papers_data, list):
                print(f"Warning: Expected list of papers in {file_path}, got {type(papers_data)}")
                return False
              # Create RDF graph
            if self.rdf_processor:
                rdf_graph = self.rdf_processor(papers_data)
            else:
                print(f"Warning: No RDF processor provided, skipping {file_path}")
                return False
            
            # Generate graph name from filename
            filename = Path(file_path).stem
            graph_name = f"http://example.org/graphs/{filename}"
            
            # Upload to Fuseki
            success = self.fuseki_client.upload_rdf_graph(rdf_graph, graph_name)
            
            if success:
                self.processed_files.add(file_path)
                print(f"Successfully processed and uploaded: {file_path}")
                
                # Also save as TTL file for backup
                ttl_path = file_path.replace('.json', '.ttl')
                rdf_graph.serialize(destination=ttl_path, format="turtle", encoding="utf-8")
                print(f"Backup TTL saved: {ttl_path}")
                
                return True
            else:
                print(f"Failed to upload RDF data for: {file_path}")
                return False
                
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in {file_path}: {e}")
            return False
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            return False

class FileWatcherService:
    def __init__(self, data_dir: str, fuseki_client: FusekiClient, rdf_processor=None):
        self.data_dir = data_dir
        self.fuseki_client = fuseki_client
        self.observer = Observer()
        self.handler = JSONFileHandler(fuseki_client, data_dir, rdf_processor)
        
    def start(self):
        """Start the file watcher service."""
        print(f"Starting file watcher for directory: {self.data_dir}")
        self.observer.schedule(self.handler, self.data_dir, recursive=False)
        self.observer.start()
        print("File watcher started successfully")
        
    def stop(self):
        """Stop the file watcher service."""
        print("Stopping file watcher...")
        self.observer.stop()
        self.observer.join()
        print("File watcher stopped")
        
    def process_existing_files(self) -> List[str]:
        """Process all existing JSON files in the data directory."""
        processed_files = []
        data_path = Path(self.data_dir)
        
        print(f"Processing existing JSON files in: {self.data_dir}")
        
        json_files = list(data_path.glob("*.json"))
        if not json_files:
            print("No JSON files found in data directory")
            return processed_files
            
        for json_file in json_files:
            print(f"Processing existing file: {json_file}")
            if self.handler.process_json_file(str(json_file)):
                processed_files.append(str(json_file))
            else:
                print(f"Failed to process: {json_file}")
                
        print(f"Finished processing {len(processed_files)} existing files")
        return processed_files
