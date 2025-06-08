"""
Enhanced file watcher service with monitoring integration for the Knowledge Graph system.
"""
import os
import time
import json
import threading
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from typing import List

from utils import create_rdf_graph_from_papers
from monitoring import system_logger, metrics_collector

class JSONFileHandler(FileSystemEventHandler):
    def __init__(self, kg_service, data_dir: str, rdf_processor=None):
        self.kg_service = kg_service
        self.data_dir = data_dir
        self.processed_files = set()
        self.rdf_processor = rdf_processor
        system_logger.log_event("info", "file_handler_init", 
                               f"JSON file handler initialized for {data_dir}")
        
    def on_created(self, event):
        """Handle file creation events."""
        if not event.is_directory and event.src_path.endswith('.json'):
            system_logger.log_event("info", "file_detected", 
                                   f"New JSON file detected: {event.src_path}")
            metrics_collector.increment_counter("files_detected")
            # Add a delay to ensure file write is complete
            time.sleep(3)
            self.process_json_file(event.src_path)
    
    def on_modified(self, event):
        """Handle file modification events."""
        if not event.is_directory and event.src_path.endswith('.json'):
            # Only process if we haven't processed this file recently
            if event.src_path not in self.processed_files:
                system_logger.log_event("info", "file_modified", 
                                       f"Modified JSON file detected: {event.src_path}")
                metrics_collector.increment_counter("files_modified")
                time.sleep(3)  # Wait for write completion
                self.process_json_file(event.src_path)
    
    def wait_for_file_stability(self, file_path: str, timeout: int = 30) -> bool:
        """Wait for file to be stable (no size changes) before processing."""
        previous_size = -1
        stable_count = 0
        
        system_logger.log_event("debug", "file_stability_check", 
                               f"Waiting for file stability: {file_path}")
        
        for _ in range(timeout):
            try:
                current_size = os.path.getsize(file_path)
                if current_size == previous_size and current_size > 0:
                    stable_count += 1
                    if stable_count >= 3:  # Stable for 3 seconds
                        system_logger.log_event("debug", "file_stable", 
                                               f"File is stable: {file_path} ({current_size} bytes)")
                        return True
                else:
                    stable_count = 0
                previous_size = current_size
                time.sleep(1)
            except (OSError, FileNotFoundError) as e:
                system_logger.log_event("warning", "file_access_error", 
                                       f"File access error: {file_path}", {"error": str(e)})
                time.sleep(1)
        
        system_logger.log_event("warning", "file_stability_timeout", 
                               f"File stability timeout: {file_path}")
        return False
    
    def process_json_file(self, file_path: str, max_retries: int = 3) -> bool:
        """Process a single JSON file and upload to Fuseki with retry logic."""
        start_time = time.time()
        
        # Wait for file to be stable before processing
        if not self.wait_for_file_stability(file_path):
            system_logger.log_file_processing(file_path, "failed", 0, 0, "File not stable")
            metrics_collector.increment_counter("files_failed_unstable")
            return False
            
        for attempt in range(max_retries):
            try:
                system_logger.log_event("info", "file_processing_attempt", 
                                       f"Processing JSON file (attempt {attempt + 1}/{max_retries}): {file_path}")
                
                # Load and validate JSON with explicit encoding
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if not content:
                        system_logger.log_file_processing(file_path, "failed", 0, 0, "File is empty")
                        metrics_collector.increment_counter("files_failed_empty")
                        return False
                    
                    papers_data = json.loads(content)
                
                if not isinstance(papers_data, list):
                    system_logger.log_event("warning", "data_format_correction", 
                                           f"Converting single paper to list: {file_path}")
                    papers_data = [papers_data]  # Convert single paper to list
                
                if not papers_data:
                    system_logger.log_file_processing(file_path, "failed", 0, 0, "No papers found")
                    metrics_collector.increment_counter("files_failed_no_data")
                    return False
                
                # Create RDF graph
                if self.rdf_processor:
                    rdf_graph = self.rdf_processor(papers_data)
                else:
                    system_logger.log_file_processing(file_path, "failed", 0, 0, "No RDF processor")
                    metrics_collector.increment_counter("files_failed_no_processor")
                    return False
                
                # Add to knowledge graph using the same method as API endpoints
                triples_added = self.kg_service.add_graph(rdf_graph)
                processing_time = time.time() - start_time
                
                if triples_added > 0:
                    self.processed_files.add(file_path)
                    system_logger.log_file_processing(file_path, "success", triples_added, processing_time)
                    metrics_collector.increment_counter("files_processed_success")
                    metrics_collector.increment_counter("triples_added", triples_added)
                    metrics_collector.record_timing("file_processing_time", processing_time)
                    
                    # Also save as TTL file for backup
                    ttl_path = file_path.replace('.json', '.ttl')
                    rdf_graph.serialize(destination=ttl_path, format="turtle", encoding="utf-8")
                    system_logger.log_event("info", "backup_created", f"Backup TTL saved: {ttl_path}")
                    
                    return True
                else:
                    system_logger.log_file_processing(file_path, "failed", 0, processing_time, "No triples added")
                    metrics_collector.increment_counter("files_failed_no_triples")
                    return False
                    
            except json.JSONDecodeError as e:
                error_msg = f"JSON decode error: {e}"
                system_logger.log_event("error", "json_decode_error", 
                                       f"JSON decode error (attempt {attempt + 1}): {file_path}", 
                                       {"error": str(e)})
                metrics_collector.increment_counter("json_decode_errors")
                
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                else:
                    self._quarantine_file(file_path, error_msg)
                    processing_time = time.time() - start_time
                    system_logger.log_file_processing(file_path, "failed", 0, processing_time, error_msg)
                    return False
                    
            except Exception as e:
                error_msg = f"Processing error: {e}"
                system_logger.log_event("error", "processing_error", 
                                       f"Processing error (attempt {attempt + 1}): {file_path}", 
                                       {"error": str(e)})
                metrics_collector.increment_counter("processing_errors")
                
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                else:
                    self._quarantine_file(file_path, error_msg)
                    processing_time = time.time() - start_time
                    system_logger.log_file_processing(file_path, "failed", 0, processing_time, error_msg)
                    return False
        
        return False
    
    def _quarantine_file(self, file_path: str, reason: str):
        """Move problematic files to a quarantine directory."""
        try:
            quarantine_dir = os.path.join(os.path.dirname(file_path), "quarantine")
            os.makedirs(quarantine_dir, exist_ok=True)
            
            filename = os.path.basename(file_path)
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            quarantine_path = os.path.join(quarantine_dir, f"{timestamp}_{filename}")
            
            os.rename(file_path, quarantine_path)
            
            # Write error report
            error_report_path = quarantine_path.replace('.json', '_error.txt')
            with open(error_report_path, 'w', encoding='utf-8') as f:
                f.write(f"Quarantined: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Original path: {file_path}\n")
                f.write(f"Reason: {reason}\n")
            
            system_logger.log_event("warning", "file_quarantined", 
                                   f"File quarantined: {file_path} -> {quarantine_path}", 
                                   {"reason": reason})
            metrics_collector.increment_counter("files_quarantined")
            
        except Exception as e:
            system_logger.log_event("error", "quarantine_failed", 
                                   f"Failed to quarantine file {file_path}", 
                                   {"error": str(e)})

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
        
        system_logger.log_event("info", "file_watcher_init", 
                               f"File watcher service initialized", 
                               {"data_dir": data_dir, "use_polling": use_polling, 
                                "poll_interval": poll_interval})
        
    def start(self):
        """Start the file watcher service."""
        system_logger.log_event("info", "file_watcher_start", 
                               f"Starting file watcher for directory: {self.data_dir}")
        
        try:
            if self.use_polling:
                system_logger.log_event("info", "polling_mode", 
                                       f"Using polling mode with {self.poll_interval}s interval")
                self.polling_active = True
                self.polling_thread = threading.Thread(target=self._polling_loop, daemon=True)
                self.polling_thread.start()
            else:
                system_logger.log_event("info", "observer_mode", "Using watchdog observer mode")
                self.observer.schedule(self.handler, self.data_dir, recursive=False)
                self.observer.start()
                
            system_logger.log_event("info", "file_watcher_started", "File watcher started successfully")
            metrics_collector.set_gauge("file_watcher_status", "active")
            
        except Exception as e:
            system_logger.log_event("error", "file_watcher_start_failed", 
                                   "Failed to start file watcher", {"error": str(e)})
            metrics_collector.set_gauge("file_watcher_status", "failed")
            raise
        
    def stop(self):
        """Stop the file watcher service."""
        system_logger.log_event("info", "file_watcher_stop", "Stopping file watcher...")
        
        try:
            if self.use_polling:
                self.polling_active = False
                if self.polling_thread:
                    self.polling_thread.join(timeout=5)
            else:
                self.observer.stop()
                self.observer.join()
                
            system_logger.log_event("info", "file_watcher_stopped", "File watcher stopped")
            metrics_collector.set_gauge("file_watcher_status", "stopped")
            
        except Exception as e:
            system_logger.log_event("error", "file_watcher_stop_failed", 
                                   "Error stopping file watcher", {"error": str(e)})
        
    def _polling_loop(self):
        """Polling loop for checking new files."""
        while self.polling_active:
            try:
                current_time = time.time()
                if current_time - self.last_scan_time >= self.poll_interval:
                    self._check_for_new_files()
                    self.last_scan_time = current_time
                    metrics_collector.increment_counter("polling_scans")
                time.sleep(1)  # Check every second if it's time to poll
            except Exception as e:
                system_logger.log_event("error", "polling_loop_error", 
                                       "Error in polling loop", {"error": str(e)})
                metrics_collector.increment_counter("polling_errors")
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
                    system_logger.log_event("info", "polling_file_detected", 
                                           f"Polling detected new/modified file: {file_path}")
                    time.sleep(1)  # Brief delay to ensure file write is complete
                    self.handler.process_json_file(file_path)
                    
        except Exception as e:
            system_logger.log_event("error", "file_check_error", 
                                   "Error checking for new files", {"error": str(e)})
        
    def process_existing_files(self) -> List[str]:
        """Process all existing JSON files in the data directory."""
        processed_files = []
        data_path = Path(self.data_dir)
        
        system_logger.log_event("info", "existing_files_scan", 
                               f"Processing existing JSON files in: {self.data_dir}")
        
        json_files = list(data_path.glob("*.json"))
        if not json_files:
            system_logger.log_event("info", "no_existing_files", "No JSON files found in data directory")
            return processed_files
            
        for json_file in json_files:
            system_logger.log_event("info", "processing_existing", f"Processing existing file: {json_file}")
            if self.handler.process_json_file(str(json_file)):
                processed_files.append(str(json_file))
            else:
                system_logger.log_event("warning", "existing_file_failed", f"Failed to process: {json_file}")
                
        system_logger.log_event("info", "existing_files_complete", 
                               f"Finished processing {len(processed_files)} existing files")
        metrics_collector.set_gauge("existing_files_processed", len(processed_files))
        
        return processed_files

    def get_status(self) -> dict:
        """Get current file watcher status and metrics."""
        return {
            "active": self.polling_active if self.use_polling else self.observer.is_alive(),
            "mode": "polling" if self.use_polling else "observer",
            "data_dir": self.data_dir,
            "processed_files_count": len(self.handler.processed_files),
            "last_scan_time": self.last_scan_time,
            "poll_interval": self.poll_interval
        }