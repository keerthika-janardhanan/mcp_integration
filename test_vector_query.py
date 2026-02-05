"""Deep debug of vector DB query"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.vector_db import VectorDBClient

def test_queries():
    vdb = VectorDBClient()
    
    test_cases = [
        {"query": "login", "where": {"type": "recorder_refined", "flow_slug": "login-floe-teest"}},
        {"query": "login", "where": {"type": "recorder_refined", "flow_slug": "login-floe teest"}},
        {"query": "login floe teest", "where": {"type": "recorder_refined", "flow_slug": "login-floe teest"}},
        {"query": "login", "where": {"type": "recorder_refined"}},
    ]
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n{'='*80}")
        print(f"Test {i}: query='{test['query']}', where={test['where']}")
        print(f"{'='*80}")
        
        try:
            results = vdb.query_where(test['query'], test['where'], top_k=5)
            print(f"Results: {len(results)} documents found")
            
            if results:
                print(f"First result:")
                print(f"  ID: {results[0].get('id')}")
                meta = results[0].get('metadata', {})
                print(f"  flow_slug: {meta.get('flow_slug')}")
                print(f"  flow_name: {meta.get('flow_name')}")
                print(f"  step_index: {meta.get('step_index')}")
        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_queries()
