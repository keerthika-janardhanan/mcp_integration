"""Debug script to test preview generation"""
import sys
import json
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.generators.agentic_script_agent import AgenticScriptAgent, FrameworkProfile

def test_preview():
    # Test scenarios
    scenarios = [
        "login floe teest",
        "login-floe-teest",
        "login-floe teest",
    ]
    
    agent = AgenticScriptAgent()
    
    for scenario in scenarios:
        print(f"\n{'='*80}")
        print(f"Testing scenario: '{scenario}'")
        print(f"{'='*80}")
        
        # Test scenario variants
        print(f"\nTesting _scenario_variants:")
        name_variants, slug_variants = agent._scenario_variants(scenario)
        print(f"  Name variants: {name_variants}")
        print(f"  Slug variants: {slug_variants}")
        
        # Gather context
        context = agent.gather_context(scenario)
        print(f"\nContext gathered:")
        print(f"  - enriched_steps length: {len(context.get('enriched_steps', ''))}")
        print(f"  - vector_steps count: {len(context.get('vector_steps', []))}")
        print(f"  - flow_available: {context.get('flow_available')}")
        
        if context.get('vector_flow'):
            print(f"  - vector_flow name: {context['vector_flow'].get('flow_name')}")
            print(f"  - vector_flow slug: {context['vector_flow'].get('flow_slug')}")
        
        vector_steps = context.get('vector_steps', [])
        if vector_steps:
            print(f"\nVector steps preview (first 3):")
            for i, step in enumerate(vector_steps[:3], 1):
                print(f"  Step {step.get('step')}: {step.get('action')} - {step.get('navigation')[:50]}...")
        
        # Try to generate preview
        try:
            # Create minimal framework profile
            framework = FrameworkProfile(
                root=Path.cwd(),
                locators_dir=Path.cwd() / "locators",
                pages_dir=Path.cwd() / "pages",
                tests_dir=Path.cwd() / "tests",
            )
            
            preview = agent.generate_preview(scenario, framework, context)
            print(f"\nPreview generated:")
            print(f"  - Length: {len(preview)}")
            if preview:
                lines = preview.split('\n')
                print(f"  - Lines: {len(lines)}")
                print(f"  - First 5 lines:")
                for line in lines[:5]:
                    print(f"    {line}")
            else:
                print("  - EMPTY PREVIEW!")
        except Exception as e:
            print(f"\nError generating preview: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_preview()
