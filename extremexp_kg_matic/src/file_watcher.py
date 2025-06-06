"""
File watcher service that monitors the data directory for new JSON files
and automatically processes them into the knowledge graph.
"""
import os
import time
import json
import threading
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from typing import List

from utils import create_rdf_graph_from_text
from fuseki_client import FusekiClient

class JSONFileHandler(FileSystemEventHandler):
    def __init__(self, kg_service, data_dir: str, rdf_processor=None):
        self.kg_service = kg_service
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
                return False            # Create RDF graph
            if self.rdf_processor:
                rdf_graph = self.rdf_processor(papers_data)
            else:
                print(f"Warning: No RDF processor provided, skipping {file_path}")
                return False
            
            # Add to knowledge graph using the same method as API endpoints
            triples_added = self.kg_service.add_graph(rdf_graph)
            
            if triples_added > 0:
                self.processed_files.add(file_path)
                print(f"Successfully processed and uploaded: {file_path}, added {triples_added} triples")
                
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
    def __init__(self, data_dir: str, kg_service, rdf_processor=None, use_polling=True, poll_interval=10):
        self.data_dir = data_dir
        self.kg_service = kg_service
        self.observer = Observer()
        self.handler = JSONFileHandler(kg_service, data_dir, rdf_processor)
        self.use_polling = use_polling
        self.poll_interval = poll_interval
        self.polling_thread = None
        self.polling_active = False
        self.last_scan_time = 0
    def start(self):
        """Start the file watcher service."""
        print(f"Starting file watcher for directory: {self.data_dir}")
        
        if self.use_polling:
            print(f"Using polling mode with {self.poll_interval}s interval")
            self.polling_active = True
            self.polling_thread = threading.Thread(target=self._polling_loop, daemon=True)
            self.polling_thread.start()
        else:
            print("Using watchdog observer mode")
            self.observer.schedule(self.handler, self.data_dir, recursive=False)
            self.observer.start()
            
        print("File watcher started successfully")
        
    def stop(self):
        """Stop the file watcher service."""
        print("Stopping file watcher...")
        
        if self.use_polling:
            self.polling_active = False
            if self.polling_thread:
                self.polling_thread.join(timeout=5)
        else:
            self.observer.stop()
            self.observer.join()
            
        print("File watcher stopped")
        
    def _polling_loop(self):
        """Polling loop for checking new files."""
        while self.polling_active:
            try:
                current_time = time.time()
                if current_time - self.last_scan_time >= self.poll_interval:
                    self._check_for_new_files()
                    self.last_scan_time = current_time
                time.sleep(1)  # Check every second if it's time to poll
            except Exception as e:
                print(f"Error in polling loop: {e}")
                time.sleep(5)  # Wait before retrying
                
    def _check_for_new_files(self):
        """Check for new or modified JSON files."""
        try:
            data_path = Path(self.data_dir)
            json_files = list(data_path.glob("*.json"))
            
            for json_file in json_files:
                file_path = str(json_file)
                file_stat = json_file.stat()
                
                # Check if file is new or modified since last scan
                if (file_path not in self.handler.processed_files and 
                    file_stat.st_mtime > self.last_scan_time):
                    print(f"Polling detected new/modified file: {file_path}")
                    time.sleep(1)  # Brief delay to ensure file write is complete
                    self.handler.process_json_file(file_path)
                    
        except Exception as e:
            print(f"Error checking for new files: {e}")
        
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
