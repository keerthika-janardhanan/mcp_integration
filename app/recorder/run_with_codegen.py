"""Run recorder with parallel Playwright codegen for complete action capture.

Usage:
    python -m app.recorder.run_with_codegen --url "https://example.com" --timeout 60
"""
import argparse
import sys
from pathlib import Path
from datetime import datetime

# Import recorder
from app.recorder.run_playwright_recorder_v2 import main as recorder_main
from app.recorder.parallel_codegen import ParallelCodegenRecorder, merge_actions
import json


def main():
    parser = argparse.ArgumentParser(description="Recorder with parallel codegen")
    parser.add_argument("--url", required=True)
    parser.add_argument("--timeout", type=int, default=None)
    parser.add_argument("--output-dir", default="recordings")
    parser.add_argument("--session-name", default=None)
    parser.add_argument("--slow-mo", type=int, default=None)
    
    args = parser.parse_args()
    
    # Setup session
    output_root = Path(args.output_dir).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    session_name = args.session_name or datetime.now().strftime("%Y%m%d_%H%M%S")
    session_dir = output_root / session_name
    session_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"[parallel] Starting recorder with parallel codegen")
    print(f"[parallel] Session: {session_dir}")
    
    # Start codegen in background
    codegen = ParallelCodegenRecorder(session_dir, args.url)
    codegen.start()
    
    # Build recorder args
    recorder_args = [
        "--url", args.url,
        "--output-dir", args.output_dir,
        "--session-name", session_name
    ]
    if args.timeout:
        recorder_args.extend(["--timeout", str(args.timeout)])
    if args.slow_mo:
        recorder_args.extend(["--slow-mo", str(args.slow_mo)])
    
    # Replace sys.argv for recorder
    original_argv = sys.argv
    sys.argv = ["run_playwright_recorder_v2.py"] + recorder_args
    
    try:
        # Run recorder
        recorder_main()
    finally:
        sys.argv = original_argv
        
        # Stop codegen
        print(f"\n[parallel] Stopping codegen...")
        codegen.stop()
        
        # Merge actions
        metadata_path = session_dir / "metadata.json"
        if metadata_path.exists():
            print(f"[parallel] Merging actions...")
            
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            recorded_actions = metadata.get('actions', [])
            codegen_actions = codegen.get_actions()
            
            print(f"[parallel] Recorded: {len(recorded_actions)} actions")
            print(f"[parallel] Codegen: {len(codegen_actions)} actions")
            
            merged_actions = merge_actions(recorded_actions, codegen_actions)
            
            # Update metadata
            metadata['actions'] = merged_actions
            metadata['codegenMerged'] = True
            metadata['codegenActionsCount'] = len(codegen_actions)
            metadata['missingActionsAdded'] = len(merged_actions) - len(recorded_actions)
            
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)
            
            print(f"\n✅ Merge complete!")
            print(f"   Added: {metadata['missingActionsAdded']} missing actions")
            print(f"   Total: {len(merged_actions)} actions")
        else:
            print(f"⚠️  No metadata.json found, skipping merge")


if __name__ == "__main__":
    main()
