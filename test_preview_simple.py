"""Simple test to verify preview generation without vector DB."""

from app.agentic_script_agent import AgenticScriptAgent

agent = AgenticScriptAgent()

# Test with test93 scenario
context = agent.gather_context("test93")

print("=" * 80)
print("CONTEXT GATHERED:")
print("=" * 80)
print(f"Flow available: {context['flow_available']}")
print(f"Flow name: {context.get('vector_flow_name', 'N/A')}")
print(f"Number of steps: {len(context.get('vector_steps', []))}")
print()

if context['vector_steps']:
    print("=" * 80)
    print("FIRST 3 STEPS:")
    print("=" * 80)
    for step in context['vector_steps'][:3]:
        print(f"Step {step.get('step')}: {step.get('action')} - {step.get('navigation', 'N/A')}")
    print()

print("=" * 80)
print("ENRICHED STEPS FOR LLM:")
print("=" * 80)
print(context['enriched_steps'][:500] + "..." if len(context['enriched_steps']) > 500 else context['enriched_steps'])
