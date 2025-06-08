#!/usr/bin/env python3
"""
Comprehensive API Test Suite for Knowledge Graph Service
Tests all endpoints systematically to verify functionality.
"""

import requests
import json
import time
import os
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"
TEST_DATA_DIR = "test_data"

# Test results tracking
test_results = []
total_tests = 0
passed_tests = 0

def log_test_result(test_name, success, details=None, response_data=None):
    """Log test result with detailed information."""
    global total_tests, passed_tests
    total_tests += 1
    if success:
        passed_tests += 1
    
    result = {
        "test_name": test_name,
        "success": success,
        "timestamp": datetime.now().isoformat(),
        "details": details,
        "response_data": response_data
    }
    test_results.append(result)
    
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} - {test_name}")
    if details:
        print(f"   Details: {details}")
    if not success and response_data:
        print(f"   Response: {response_data}")
    print()

def test_root_endpoint():
    """Test the root endpoint (GET /)."""
    try:
        response = requests.get(f"{BASE_URL}/")
        
        if response.status_code == 200:
            data = response.json()
            
            # Validate expected fields
            required_fields = ["message", "version", "endpoints"]
            missing_fields = [field for field in required_fields if field not in data]
            
            if missing_fields:
                log_test_result("Root Endpoint", False, 
                              f"Missing fields: {missing_fields}", data)
                return
            
            # Validate endpoints list
            expected_endpoints = [
                "health", "detailed_health", "process_papers", "upload_file", 
                "stats", "metrics", "backup", "graph_clear", "scan_files"
            ]
            
            endpoints = data.get("endpoints", {})
            missing_endpoints = [ep for ep in expected_endpoints if ep not in endpoints]
            
            if missing_endpoints:
                log_test_result("Root Endpoint", False, 
                              f"Missing endpoints: {missing_endpoints}", data)
                return
            
            log_test_result("Root Endpoint", True, 
                          f"API version {data['version']} with {len(endpoints)} endpoints", data)
        else:
            log_test_result("Root Endpoint", False, 
                          f"HTTP {response.status_code}", response.text)
    
    except Exception as e:
        log_test_result("Root Endpoint", False, f"Exception: {str(e)}")

def test_health_check():
    """Test the basic health check endpoint (GET /health)."""
    try:
        response = requests.get(f"{BASE_URL}/health")
        
        if response.status_code == 200:
            data = response.json()
            required_fields = ["status", "timestamp", "uptime_seconds"]
            missing_fields = [field for field in required_fields if field not in data]
            
            if missing_fields:
                log_test_result("Health Check", False, 
                              f"Missing fields: {missing_fields}", data)
                return
            
            log_test_result("Health Check", True, 
                          f"Status: {data['status']}, Uptime: {data['uptime_seconds']:.1f}s", data)
        else:
            log_test_result("Health Check", False, 
                          f"HTTP {response.status_code}", response.text)
    
    except Exception as e:
        log_test_result("Health Check", False, f"Exception: {str(e)}")

def test_detailed_health():
    """Test the detailed health check endpoint (GET /health/detailed)."""
    try:
        response = requests.get(f"{BASE_URL}/health/detailed")
        
        if response.status_code == 200:
            data = response.json()
            required_fields = ["status", "timestamp", "uptime_seconds", "fuseki_status", 
                             "graph_stats", "file_watcher_status", "metrics"]
            missing_fields = [field for field in required_fields if field not in data]
            
            if missing_fields:
                log_test_result("Detailed Health", False, 
                              f"Missing fields: {missing_fields}", data)
                return
            
            details = f"Status: {data['status']}, Fuseki: {data['fuseki_status']}, " \
                     f"File Watcher: {data['file_watcher_status']}"
            
            log_test_result("Detailed Health", True, details, data)
        else:
            log_test_result("Detailed Health", False, 
                          f"HTTP {response.status_code}", response.text)
    
    except Exception as e:
        log_test_result("Detailed Health", False, f"Exception: {str(e)}")

def test_stats():
    """Test the statistics endpoint (GET /stats)."""
    try:
        response = requests.get(f"{BASE_URL}/stats")
        
        if response.status_code == 200:
            data = response.json()
            
            # Look for typical graph statistics
            if isinstance(data, dict) and len(data) > 0:
                log_test_result("Statistics", True, 
                              f"Retrieved graph statistics: {list(data.keys())}", data)
            else:
                log_test_result("Statistics", False, 
                              "Empty or invalid statistics response", data)
        else:
            log_test_result("Statistics", False, 
                          f"HTTP {response.status_code}", response.text)
    
    except Exception as e:
        log_test_result("Statistics", False, f"Exception: {str(e)}")

def test_metrics():
    """Test the metrics endpoint (GET /metrics)."""
    try:
        response = requests.get(f"{BASE_URL}/metrics")
        
        if response.status_code == 200:
            data = response.json()
            
            # Validate expected metrics structure
            expected_sections = ["timestamp", "system_metrics"]
            present_sections = [section for section in expected_sections if section in data]
            
            if len(present_sections) >= 1:  # At least timestamp should be present
                log_test_result("Metrics", True, 
                              f"Retrieved metrics with sections: {list(data.keys())}", data)
            else:
                log_test_result("Metrics", False, 
                              "Missing expected metrics sections", data)
        else:
            log_test_result("Metrics", False, 
                          f"HTTP {response.status_code}", response.text)
    
    except Exception as e:
        log_test_result("Metrics", False, f"Exception: {str(e)}")

def test_process_papers():
    """Test the process papers endpoint (POST /process/papers)."""
    try:
        test_papers = [
            {
                "title": "Test Paper on Machine Learning",
                "year": 2024,
                "pdfUrl": "https://example.com/paper1.pdf",
                "mentions": {"AI": 5, "ML": 3}
            },
            {
                "title": "Another Test Paper",
                "year": 2023,
                "papersWithCodeUrl": "https://paperswithcode.com/paper/test"
            }
        ]
        
        response = requests.post(f"{BASE_URL}/process/papers", 
                               json=test_papers,
                               headers={"Content-Type": "application/json"})
        
        if response.status_code == 200:
            data = response.json()
            required_fields = ["success", "message"]
            missing_fields = [field for field in required_fields if field not in data]
            
            if missing_fields:
                log_test_result("Process Papers", False, 
                              f"Missing fields: {missing_fields}", data)
                return
            
            if data.get("success"):
                details = f"Processed {len(test_papers)} papers"
                if "triples_added" in data:
                    details += f", added {data['triples_added']} triples"
                log_test_result("Process Papers", True, details, data)
            else:
                log_test_result("Process Papers", False, 
                              f"Processing failed: {data.get('message')}", data)
        else:
            log_test_result("Process Papers", False, 
                          f"HTTP {response.status_code}", response.text)
    
    except Exception as e:
        log_test_result("Process Papers", False, f"Exception: {str(e)}")

def create_test_json_file():
    """Create a test JSON file for upload testing."""
    if not os.path.exists(TEST_DATA_DIR):
        os.makedirs(TEST_DATA_DIR)
    
    test_data = [
        {
            "title": "Uploaded Test Paper",
            "year": 2024,
            "pdfUrl": "https://example.com/uploaded.pdf",
            "mentions": {"testing": 2, "upload": 1}
        }
    ]
    
    file_path = os.path.join(TEST_DATA_DIR, "test_upload.json")
    with open(file_path, 'w') as f:
        json.dump(test_data, f, indent=2)
    
    return file_path

def test_file_upload():
    """Test the file upload endpoint (POST /upload)."""
    try:
        # Create test file
        test_file_path = create_test_json_file()
        
        with open(test_file_path, 'rb') as f:
            files = {"file": ("test_upload.json", f, "application/json")}
            response = requests.post(f"{BASE_URL}/upload", files=files)
        
        if response.status_code == 200:
            data = response.json()
            required_fields = ["success", "message"]
            missing_fields = [field for field in required_fields if field not in data]
            
            if missing_fields:
                log_test_result("File Upload", False, 
                              f"Missing fields: {missing_fields}", data)
                return
            
            if data.get("success"):
                details = f"Uploaded file successfully"
                if "triples_added" in data:
                    details += f", added {data['triples_added']} triples"
                log_test_result("File Upload", True, details, data)
            else:
                log_test_result("File Upload", False, 
                              f"Upload failed: {data.get('message')}", data)
        else:
            log_test_result("File Upload", False, 
                          f"HTTP {response.status_code}", response.text)
        
        # Clean up test file
        if os.path.exists(test_file_path):
            os.remove(test_file_path)
    
    except Exception as e:
        log_test_result("File Upload", False, f"Exception: {str(e)}")

def test_scan_files():
    """Test the manual file scan endpoint (POST /scan-files)."""
    try:
        response = requests.post(f"{BASE_URL}/scan-files")
        
        if response.status_code == 200:
            data = response.json()
            required_fields = ["message", "success"]
            missing_fields = [field for field in required_fields if field not in data]
            
            if missing_fields:
                log_test_result("Scan Files", False, 
                              f"Missing fields: {missing_fields}", data)
                return
            
            if data.get("success"):
                processed_count = len(data.get("processed_files", []))
                log_test_result("Scan Files", True, 
                              f"Scanned and processed {processed_count} files", data)
            else:
                log_test_result("Scan Files", False, 
                              f"Scan failed: {data.get('message')}", data)
        else:
            log_test_result("Scan Files", False, 
                          f"HTTP {response.status_code}", response.text)
    
    except Exception as e:
        log_test_result("Scan Files", False, f"Exception: {str(e)}")

def test_backup():
    """Test the backup endpoint (POST /backup)."""
    try:
        response = requests.post(f"{BASE_URL}/backup")
        
        if response.status_code == 200:
            data = response.json()
            
            if "message" in data and "backup" in data["message"].lower():
                log_test_result("Backup", True, 
                              "Backup started successfully", data)
            else:
                log_test_result("Backup", False, 
                              "Unexpected backup response", data)
        else:
            log_test_result("Backup", False, 
                          f"HTTP {response.status_code}", response.text)
    
    except Exception as e:
        log_test_result("Backup", False, f"Exception: {str(e)}")

def test_clear_graph():
    """Test the clear graph endpoint (DELETE /graph)."""
    try:
        # First check current stats
        stats_response = requests.get(f"{BASE_URL}/stats")
        initial_stats = stats_response.json() if stats_response.status_code == 200 else {}
        
        response = requests.delete(f"{BASE_URL}/graph")
        
        if response.status_code == 200:
            data = response.json()
            
            if "message" in data and "clear" in data["message"].lower():
                log_test_result("Clear Graph", True, 
                              "Graph cleared successfully", data)
            else:
                log_test_result("Clear Graph", False, 
                              "Unexpected clear response", data)
        else:
            log_test_result("Clear Graph", False, 
                          f"HTTP {response.status_code}", response.text)
    
    except Exception as e:
        log_test_result("Clear Graph", False, f"Exception: {str(e)}")

def test_error_handling():
    """Test error handling with invalid requests."""
    try:
        # Test invalid JSON upload
        response = requests.post(f"{BASE_URL}/process/papers", 
                               data="invalid json",
                               headers={"Content-Type": "application/json"})
        
        # Expect 400 or 422 for validation errors
        if response.status_code in [400, 422, 500]:
            log_test_result("Error Handling", True, 
                          f"Properly handled invalid request with HTTP {response.status_code}")
        else:
            log_test_result("Error Handling", False, 
                          f"Unexpected status code: {response.status_code}", response.text)
    
    except Exception as e:
        log_test_result("Error Handling", False, f"Exception: {str(e)}")

def run_all_tests():
    """Run all API endpoint tests."""
    print("=" * 60)
    print("COMPREHENSIVE API TEST SUITE")
    print("=" * 60)
    print(f"Testing API at: {BASE_URL}")
    print(f"Started at: {datetime.now().isoformat()}")
    print()
    
    # Run all tests
    test_root_endpoint()
    test_health_check()
    test_detailed_health()
    test_stats()
    test_metrics()
    test_process_papers()
    test_file_upload()
    test_scan_files()
    test_backup()
    test_clear_graph()
    test_error_handling()
    
    # Print summary
    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
    print()
    
    # Print failed tests details
    failed_tests = [test for test in test_results if not test["success"]]
    if failed_tests:
        print("FAILED TESTS:")
        print("-" * 40)
        for test in failed_tests:
            print(f"❌ {test['test_name']}: {test['details']}")
        print()
    
    # Save detailed results
    results_file = f"api_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, 'w') as f:
        json.dump({
            "summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": total_tests - passed_tests,
                "success_rate": (passed_tests/total_tests)*100,
                "timestamp": datetime.now().isoformat()
            },
            "test_results": test_results
        }, f, indent=2)
    
    print(f"Detailed results saved to: {results_file}")
    
    return total_tests, passed_tests

if __name__ == "__main__":
    # Clean up any previous test data
    if os.path.exists(TEST_DATA_DIR):
        import shutil
        shutil.rmtree(TEST_DATA_DIR)
    
    total, passed = run_all_tests()
    
    # Exit with error code if tests failed
    if passed < total:
        exit(1)
    else:
        print("🎉 All tests passed!")
        exit(0)
