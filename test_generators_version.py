"""Test the generators version of agentic_script_agent"""

from app.generators.agentic_script_agent import AgenticScriptAgent

agent = AgenticScriptAgent()
context = agent.gather_context("test93")

print("=" * 80)
print("CONTEXT FROM GENERATORS VERSION:")
print("=" * 80)
print(f"Flow available: {context['flow_available']}")
print(f"Flow name: {context.get('vector_flow', {}).get('flow_name', 'N/A')}")
print(f"Number of steps: {len(context.get('vector_steps', []))}")
print()

print("=" * 80)
print("ENRICHED STEPS:")
print("=" * 80)
print(context['enriched_steps'])
