#!/usr/bin/env python3
"""
Test script to verify the ExtremeXP KG system is working correctly.
"""
import requests
import json
import time
import sys
from pathlib import Path

def test_fuseki_connectivity():
    """Test if Fuseki is accessible."""
    try:
        response = requests.get("http://localhost:3030/$/ping", timeout=5)
        if response.status_code == 200:
            print("✓ Fuseki is accessible")
            return True
        else:
            print(f"✗ Fuseki ping failed with status: {response.status_code}")
            return False
    except requests.RequestException as e:
        print(f"✗ Fuseki connection failed: {e}")
        return False

def test_query_knowledge_graph():
    """Test querying the knowledge graph."""
    try:
        query = """
        SELECT (COUNT(*) AS ?count) WHERE { 
            ?s ?p ?o 
        }
        """
        
        response = requests.post(
            "http://localhost:3030/matic_papers_kg/sparql",
            data={"query": query},
            headers={"Accept": "application/sparql-results+json"},
            timeout=10
        )
        
        if response.status_code == 200:
            results = response.json()
            count = int(results["results"]["bindings"][0]["count"]["value"])
            print(f"✓ Knowledge graph contains {count} triples")
            return True, count
        else:
            print(f"✗ SPARQL query failed with status: {response.status_code}")
            return False, 0
            
    except Exception as e:
        print(f"✗ SPARQL query error: {e}")
        return False, 0

def test_papers_query():
    """Test querying for papers in the knowledge graph."""
    try:
        query = """
        PREFIX ex: <http://example.org/>
        SELECT ?paper ?title WHERE { 
            ?paper a ex:Paper .
            ?paper ex:paper_title ?title .
        } LIMIT 10
        """
        
        response = requests.post(
            "http://localhost:3030/matic_papers_kg/sparql",
            data={"query": query},
            headers={"Accept": "application/sparql-results+json"},
            timeout=10
        )
        
        if response.status_code == 200:
            results = response.json()
            papers = results["results"]["bindings"]
            print(f"✓ Found {len(papers)} papers in the knowledge graph")
            
            if papers:
                print("Sample papers:")
                for i, paper in enumerate(papers[:3]):
                    title = paper["title"]["value"][:60] + "..." if len(paper["title"]["value"]) > 60 else paper["title"]["value"]
                    print(f"  {i+1}. {title}")
            
            return True, len(papers)
        else:
            print(f"✗ Papers query failed with status: {response.status_code}")
            return False, 0
            
    except Exception as e:
        print(f"✗ Papers query error: {e}")
        return False, 0

def create_test_json_file():
    """Create a test JSON file to verify file watching works."""
    test_data = [
        {
            "title": "Test Paper: Automated Knowledge Graph Generation",
            "url": "https://example.com/test_paper_2024.pdf",
            "origin": "https://paperswithcode.com/test-paper",
            "tasks": ["Knowledge Graph Construction", "Information Extraction"],
            "datasets": ["Test Dataset", "Synthetic Data"],
            "methods": ["Neural Networks", "Graph Neural Networks"],
            "results": [
                {
                    "task": "Knowledge Graph Construction",
                    "dataset": "Test Dataset",
                    "metric": "F1-Score",
                    "value": "85.6%",
                    "model": "GNN-Based Extractor",
                    "rank": 1
                }
            ]
        }
    ]
    
    # Save test file
    test_file = Path("./data/test_paper.json")
    with open(test_file, 'w', encoding='utf-8') as f:
        json.dump(test_data, f, indent=2)
    
    print(f"✓ Created test file: {test_file}")
    return str(test_file)

def run_tests():
    """Run all tests."""
    print("=== ExtremeXP KG System Test ===\n")
    
    # Test 1: Fuseki connectivity
    print("1. Testing Fuseki connectivity...")
    if not test_fuseki_connectivity():
        print("FAIL: Fuseki is not accessible. Make sure docker-compose is running.")
        return False
    
    # Test 2: Query existing data
    print("\n2. Testing knowledge graph queries...")
    success, triple_count = test_query_knowledge_graph()
    if not success:
        print("FAIL: Cannot query knowledge graph")
        return False
    
    # Test 3: Query papers
    print("\n3. Testing papers query...")
    success, paper_count = test_papers_query()
    if not success:
        print("FAIL: Cannot query papers")
        return False
    
    # Test 4: File watching (if no existing data)
    if triple_count == 0:
        print("\n4. Testing file watching with new JSON file...")
        test_file = create_test_json_file()
        print("Waiting 10 seconds for file to be processed...")
        time.sleep(10)
        
        # Check if data was added
        success, new_count = test_query_knowledge_graph()
        if success and new_count > 0:
            print(f"✓ File watching works! Added {new_count} triples")
        else:
            print("✗ File watching may not be working")
    
    print(f"\n=== Test Summary ===")
    print(f"✓ Fuseki: Connected")
    print(f"✓ Knowledge Graph: {triple_count} triples")
    print(f"✓ Papers: {paper_count} papers found")
    print(f"✓ System Status: OPERATIONAL")
    
    return True

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
