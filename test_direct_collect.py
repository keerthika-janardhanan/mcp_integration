"""Direct test of _collect_vector_flow_steps"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.generators.agentic_script_agent import AgenticScriptAgent

def test_collection():
    agent = AgenticScriptAgent()
    
    print("Testing _collect_vector_flow_steps directly:")
    print("="*80)
    
    # Add some instrumentation
    original_query = agent.vector_db.query_where
    call_count = [0]
    
    def instrumented_query(query, where, top_k=10):
        call_count[0] += 1
        print(f"\nCall #{call_count[0]}:")
        print(f"  query: '{query}'")
        print(f"  where: {where}")
        result = original_query(query, where, top_k)
        print(f"  results: {len(result or [])} documents")
        if result:
            print(f"  first result flow_slug: {result[0].get('metadata', {}).get('flow_slug')}")
        return result
    
    agent.vector_db.query_where = instrumented_query
    
    steps = agent._collect_vector_flow_steps("login floe teest", top_k=10)
    
    print(f"\n{'='*80}")
    print(f"FINAL RESULT: {len(steps)} steps collected")
    print(f"Total vector_db.query_where calls: {call_count[0]}")
    
    if steps:
        print(f"\nFirst step:")
        print(f"  step: {steps[0].get('step')}")
        print(f"  action: {steps[0].get('action')}")
        print(f"  navigation: {steps[0].get('navigation')[:50]}...")
        print(f"  flow_slug: {steps[0].get('flow_slug')}")

if __name__ == "__main__":
    test_collection()
