#!/usr/bin/env python3
"""
Simple script to test the orchestrator flow without webhook.

Usage:
    python test_orchestrator_flow.py EPIC-123
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.orchestrator import process_epic
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_orchestrator_flow.py EPIC-KEY [python|java] [--github]")
        print()
        print("Examples:")
        print("  python test_orchestrator_flow.py EPIC-123")
        print("  python test_orchestrator_flow.py EPIC-123 python")
        print("  python test_orchestrator_flow.py EPIC-123 java --github")
        print()
        print("Arguments:")
        print("  EPIC-KEY    : Jira Epic key (required)")
        print("  language    : 'python' (pytest) or 'java' (RestAssured), default: python")
        print("  --github    : Push to GitHub (triggers Jenkins pipeline)")
        sys.exit(1)
    
    epic_key = sys.argv[1]
    language = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] in ['python', 'java'] else 'python'
    push_to_github = '--github' in sys.argv
    
    framework = 'pytest' if language == 'python' else 'RestAssured'
    
    print("="*60)
    print(f"Testing Orchestrator Flow")
    print("="*60)
    print(f"Epic Key:  {epic_key}")
    print(f"Language:  {language.upper()} ({framework})")
    print(f"GitHub:    {'Yes (triggers Jenkins)' if push_to_github else 'No (local only)'}")
    print("="*60)
    print()
    
    try:
        # Run the orchestration flow
        results = process_epic(
            issue_key=epic_key,
            language=language,
            save_to_github=push_to_github,  # Push to GitHub (triggers Jenkins)
            save_locally=True                # Always save locally
        )
        
        print()
        print("="*60)
        print("✅ SUCCESS!")
        print("="*60)
        
        if results.get('output_dir'):
            print(f"📁 Local tests:  {results['output_dir']}")
        
        if results.get('github_branch'):
            print(f"🔀 GitHub branch: {results['github_branch']}")
            print(f"🔄 Jenkins pipeline will run automatically")
        
        print()
        print("Next steps:")
        if results.get('output_dir'):
            print(f"  1. Review tests: {results['output_dir']}")
        if results.get('github_branch'):
            print(f"  2. Monitor Jenkins pipeline for test execution")
            print(f"  3. Check Jira Epic for test results")
        
    except Exception as e:
        print()
        print("="*60)
        print("❌ FAILED!")
        print("="*60)
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()

