#!/usr/bin/env python3
"""
Simple script to test the orchestrator flow without webhook.

Usage:
    python test_orchestrator_flow.py EPIC-123
"""

import sys
import os
import argparse

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.orchestrator import process_epic
from core.epic_runner import run_polling_runner
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def main():
    parser = argparse.ArgumentParser(description='Test orchestrator or start a polling runner.')
    parser.add_argument('--jira_name', dest='jira_name', help='Jira Epic key for direct run (e.g., KAN-4)')
    parser.add_argument('--language', dest='language', choices=['python', 'java'], default='python', help='Test language')
    parser.add_argument('--jenkins', dest='jenkins', choices=['yes', 'no'], default='no', help='Push to GitHub (triggers Jenkins)')
    parser.add_argument('--runner', dest='runner', choices=['on', 'off'], default='off', help='Start polling runner')
    
    args = parser.parse_args()
    push_to_github = args.jenkins == 'yes'
    framework = 'pytest' if args.language == 'python' else 'RestAssured'

    if args.runner == 'on':
        print("="*60)
        print("Starting Polling Runner")
        print("="*60)
        print(f"Language:  {args.language.upper()} ({framework})")
        print(f"GitHub:    {'Yes (triggers Jenkins)' if push_to_github else 'No (local only)'}")
        print()
        run_polling_runner(language=args.language, push_to_github=push_to_github)
        return

    if not args.jira_name:
        print("--jira_name is required when --runner=off")
        sys.exit(1)

    epic_key = args.jira_name
    print("="*60)
    print(f"Testing Orchestrator Flow")
    print("="*60)
    print(f"Epic Key:  {epic_key}")
    print(f"Language:  {args.language.upper()} ({framework})")
    print(f"GitHub:    {'Yes (triggers Jenkins)' if push_to_github else 'No (local only)'}")
    print("="*60)
    print()

    try:
        results = process_epic(
            issue_key=epic_key,
            language=args.language,
            save_to_github=push_to_github,
            save_locally=True
        )

        print()
        print("="*60)
        if results.get('skipped'):
            print("🛑 Skipped by eligibility gate.")
        else:
            print("✅ SUCCESS!")
        print("="*60)

        if results.get('output_dir'):
            print(f"📁 Local tests:  {results['output_dir']}")
            # Surface metadata file if present
            import os
            meta = os.path.join(results['output_dir'], 'metadata.json')
            if os.path.exists(meta):
                print(f"🧠 AI metadata: {meta}")

        if results.get('github_branch'):
            print(f"🔀 GitHub branch: {results['github_branch']}")
            print(f"🔄 Jenkins pipeline will run automatically")

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

