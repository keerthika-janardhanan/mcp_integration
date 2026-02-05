import sys
import os
sys.path.insert(0, 'app')
os.chdir('app')

from pathlib import Path
import json
import re

def _slugify(value: str, default: str = "scenario") -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower())
    value = re.sub(r"-+", "-", value).strip("-")
    return value or default

def _scenario_variants(scenario: str):
    raw = (scenario or "").strip()
    if not raw:
        return [], []
    
    variants = [raw]
    slug_variants = [_slugify(raw)]
    
    print(f"Scenario: {scenario}")
    print(f"Name variants: {variants}")
    print(f"Slug variants: {slug_variants}")
    
    return variants, slug_variants

def test_load_flow(scenario: str):
    name_variants, slug_variants = _scenario_variants(scenario)
    
    generated_dir = Path(__file__).resolve().parent / "app" / "generated_flows"
    print(f"\nGenerated flows directory: {generated_dir}")
    print(f"Directory exists: {generated_dir.exists()}")
    
    if not generated_dir.exists():
        print("ERROR: Directory does not exist!")
        return
    
    files = list(generated_dir.glob("*.refined.json"))
    print(f"\nFound {len(files)} .refined.json files:")
    for f in files:
        print(f"  - {f.name}")
    
    slug_lower = [s.lower() for s in slug_variants if s]
    name_lower = [n.lower() for n in name_variants if n]
    
    print(f"\nSearching with:")
    print(f"  slug_lower: {slug_lower}")
    print(f"  name_lower: {name_lower}")
    
    for path in files:
        stem_lower = path.stem.lower()
        print(f"\n  Checking: {path.name}")
        print(f"    stem_lower: {stem_lower}")
        
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            flow_name = str(data.get("flow_name") or path.stem)
            flow_slug = _slugify(flow_name)
            
            print(f"    flow_name: {flow_name}")
            print(f"    flow_slug: {flow_slug}")
            
            matches = False
            if slug_lower and flow_slug.lower() in slug_lower:
                matches = True
                print(f"    ✓ MATCHED by flow_slug")
            elif any(slug in stem_lower for slug in slug_lower):
                matches = True
                print(f"    ✓ MATCHED by stem")
            elif name_lower and flow_name.lower() in name_lower:
                matches = True
                print(f"    ✓ MATCHED by flow_name")
            else:
                print(f"    ✗ No match")
            
            if matches:
                steps = data.get("steps") or []
                print(f"    Found {len(steps)} steps!")
                return steps
        except Exception as e:
            print(f"    ERROR: {e}")
    
    print("\n✗ No matching flow found")
    return []

if __name__ == "__main__":
    test_load_flow("chines")
