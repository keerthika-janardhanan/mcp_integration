"""CLI tool for enhanced recording with zero-loss capture.

Usage:
    # Basic recording with all enhancements
    python -m app.recorder.enhanced_recorder_cli --url "https://example.com" --session demo1
    
    # Recording with specific features
    python -m app.recorder.enhanced_recorder_cli --url "https://example.com" --no-ai --verbose
    
    # Verify existing recording
    python -m app.recorder.enhanced_recorder_cli --verify recordings/demo1
    
    # Check feature availability
    python -m app.recorder.enhanced_recorder_cli --check-features
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    from playwright.async_api import async_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False
    logger.error("Playwright not installed. Install with: pip install playwright")

try:
    from app.recorder.enhanced_recorder_integration import (
        EnhancedRecorderSession,
        is_enhancement_available,
        print_feature_status
    )
    HAS_ENHANCED_RECORDER = True
except ImportError:
    HAS_ENHANCED_RECORDER = False
    logger.error("Enhanced recorder not available")

try:
    from app.recorder.ai_verification_agent import verify_recording_session
    HAS_VERIFICATION = True
except ImportError:
    HAS_VERIFICATION = False


async def run_enhanced_recording(
    url: str,
    session_name: str,
    output_dir: Path,
    browser_type: str = "chromium",
    headless: bool = False,
    enable_mcp: bool = True,
    enable_ai: bool = True,
    capture_dom: bool = True,
    capture_screenshots: bool = True,
    verbose: bool = False
) -> Optional[dict]:
    """Run enhanced recording session.
    
    Args:
        url: Starting URL
        session_name: Session name
        output_dir: Output directory
        browser_type: Browser type (chromium, firefox, webkit)
        headless: Run in headless mode
        enable_mcp: Enable MCP features
        enable_ai: Enable AI verification
        capture_dom: Capture DOM snapshots
        capture_screenshots: Capture screenshots
        verbose: Verbose logging
        
    Returns:
        Recording result dictionary
    """
    if not HAS_PLAYWRIGHT:
        logger.error("Playwright not available")
        return None
    
    if not HAS_ENHANCED_RECORDER:
        logger.error("Enhanced recorder not available")
        return None
    
    session_dir = output_dir / session_name
    session_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Starting enhanced recording: {session_name}")
    logger.info(f"URL: {url}")
    logger.info(f"Output: {session_dir}")
    logger.info(f"Features: MCP={enable_mcp}, AI={enable_ai}")
    
    async with async_playwright() as p:
        # Launch browser
        browser_launcher = getattr(p, browser_type)
        browser = await browser_launcher.launch(headless=headless)
        
        # Create context and page
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = await context.new_page()
        
        # Create enhanced session
        session = EnhancedRecorderSession(
            session_dir=session_dir,
            capture_dom=capture_dom,
            capture_screenshots=capture_screenshots,
            enable_mcp=enable_mcp,
            enable_ai_verification=enable_ai,
            verbose=verbose
        )
        
        try:
            # Start recording
            await session.start(page, url)
            
            print("\n" + "="*60)
            print("🎥 ENHANCED RECORDING ACTIVE")
            print("="*60)
            print("  Perform your actions in the browser...")
            print("  Press Ctrl+C when done to stop and finalize")
            print("="*60 + "\n")
            
            # Wait for user to finish
            try:
                while session.is_recording:
                    await asyncio.sleep(1)
                    
                    # Show stats every 5 seconds
                    if verbose:
                        stats = session.get_real_time_stats()
                        if stats["events_captured"] > 0 and stats["events_captured"] % 5 == 0:
                            logger.info(f"Events captured: {stats['events_captured']}")
            
            except KeyboardInterrupt:
                logger.info("\n📝 Stopping recording...")
            
            # Finalize
            result = await session.stop_and_finalize()
            
            # Print summary
            print("\n" + "="*60)
            print("✅ RECORDING COMPLETE")
            print("="*60)
            print(f"  Events Captured:     {result['statistics']['events_captured']}")
            print(f"  DOM Mutations:       {result['statistics'].get('dom_mutations', 0)}")
            print(f"  Snapshots:           {result['statistics'].get('snapshots_taken', 0)}")
            
            if result['verification']:
                status = result['verification'].get('capture_status', 'UNKNOWN')
                print(f"  Verification:        {status}")
                
                if 'ai_analysis' in result['verification']:
                    ai = result['verification']['ai_analysis']
                    if not ai.get('has_gaps', True):
                        print("  AI Analysis:         ✅ PASSED")
                    else:
                        print(f"  AI Analysis:         ⚠️  {ai.get('missing_steps_count', 0)} potential gaps")
            
            print(f"\n  Reports Generated:   {len(result['reports'])}")
            for report in result['reports']:
                print(f"    - {report}")
            
            print("="*60 + "\n")
            
            return result
        
        finally:
            await browser.close()


async def verify_existing_recording(session_dir: Path) -> None:
    """Verify an existing recording session.
    
    Args:
        session_dir: Path to recording session
    """
    if not HAS_VERIFICATION:
        logger.error("AI verification not available")
        return
    
    logger.info(f"Verifying recording: {session_dir}")
    
    try:
        result, report_path = verify_recording_session(session_dir)
        
        print("\n" + "="*60)
        print("📊 VERIFICATION RESULTS")
        print("="*60)
        print(f"  Status:       {'✅ PASSED' if not result.has_gaps else '⚠️  GAPS DETECTED'}")
        print(f"  Confidence:   {result.confidence:.0%}")
        print(f"  Missing Steps: {len(result.missing_steps)}")
        print(f"\n  Summary:\n    {result.analysis_summary}")
        
        if result.missing_steps:
            print(f"\n  Suspected Gaps:")
            for i, step in enumerate(result.missing_steps[:5], 1):
                print(f"    {i}. {step['likely_action']} (confidence: {step['confidence']:.0%})")
        
        print(f"\n  Recommendations:")
        for rec in result.recommendations:
            print(f"    - {rec}")
        
        print(f"\n  Full Report: {report_path}")
        print("="*60 + "\n")
    
    except Exception as e:
        logger.error(f"Verification failed: {e}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Enhanced Recorder CLI - Zero-loss event capture with AI verification",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Record with all features
  python -m app.recorder.enhanced_recorder_cli --url "https://app.example.com" --session demo1
  
  # Record without AI verification
  python -m app.recorder.enhanced_recorder_cli --url "https://app.example.com" --no-ai
  
  # Verify existing recording
  python -m app.recorder.enhanced_recorder_cli --verify recordings/demo1
  
  # Check feature availability
  python -m app.recorder.enhanced_recorder_cli --check-features
        """
    )
    
    # Recording options
    parser.add_argument(
        "--url",
        help="Starting URL for recording"
    )
    parser.add_argument(
        "--session",
        default="enhanced_session",
        help="Session name (default: enhanced_session)"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("recordings"),
        help="Output directory (default: recordings)"
    )
    parser.add_argument(
        "--browser",
        choices=["chromium", "firefox", "webkit"],
        default="chromium",
        help="Browser type (default: chromium)"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run in headless mode"
    )
    
    # Feature toggles
    parser.add_argument(
        "--no-mcp",
        action="store_true",
        help="Disable MCP enhancements"
    )
    parser.add_argument(
        "--no-ai",
        action="store_true",
        help="Disable AI verification"
    )
    parser.add_argument(
        "--no-dom",
        action="store_true",
        help="Disable DOM capture"
    )
    parser.add_argument(
        "--no-screenshots",
        action="store_true",
        help="Disable screenshot capture"
    )
    
    # Verification mode
    parser.add_argument(
        "--verify",
        type=Path,
        metavar="SESSION_DIR",
        help="Verify existing recording session"
    )
    
    # Utilities
    parser.add_argument(
        "--check-features",
        action="store_true",
        help="Check feature availability"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output"
    )
    
    args = parser.parse_args()
    
    # Set log level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Check features mode
    if args.check_features:
        print_feature_status()
        return 0
    
    # Verify mode
    if args.verify:
        asyncio.run(verify_existing_recording(args.verify))
        return 0
    
    # Recording mode - require URL
    if not args.url:
        parser.error("--url is required for recording (or use --verify for verification mode)")
    
    # Run recording
    result = asyncio.run(run_enhanced_recording(
        url=args.url,
        session_name=args.session,
        output_dir=args.output_dir,
        browser_type=args.browser,
        headless=args.headless,
        enable_mcp=not args.no_mcp,
        enable_ai=not args.no_ai,
        capture_dom=not args.no_dom,
        capture_screenshots=not args.no_screenshots,
        verbose=args.verbose
    ))
    
    if result:
        # Exit with status based on verification
        if result['verification'].get('ai_analysis', {}).get('has_gaps'):
            return 1  # Warning status
        return 0
    else:
        return 2  # Error


if __name__ == "__main__":
    sys.exit(main())
