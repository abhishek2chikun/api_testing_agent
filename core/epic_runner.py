"""
Polling runner that periodically searches for Jira Epics by prefix
and triggers the orchestrator for each new/updated Epic.
"""
import logging
import time
from typing import Set

from config.loader import get_config_value
from integrations.jira.client import find_recent_epics_by_prefix
from core.orchestrator import process_epic


def run_polling_runner(language: str = 'python', push_to_github: bool = False) -> None:
    """
    Continuous loop that:
      - Reads runner.time_sleep and runner.prefix_jira_name from config
      - Searches for recent Epics in that project
      - Triggers orchestration for each Epic (skip duplicates in a short cache)
    """
    sleep_seconds = int(get_config_value('runner.time_sleep', 60))
    prefix = str(get_config_value('runner.prefix_jira_name', '')).strip()
    max_per_cycle = int(get_config_value('runner.max_per_cycle', 5))

    if not prefix:
        logging.error('Runner requires runner.prefix_jira_name in config/config.yaml')
        return

    logging.info('Starting Jira polling runner: project=%s, interval=%ss, max_per_cycle=%s', prefix, sleep_seconds, max_per_cycle)

    # Simple in-memory cache to avoid immediate repeats
    recently_processed: Set[str] = set()

    while True:
        try:
            issues = find_recent_epics_by_prefix(prefix, limit=max_per_cycle)
            if not issues:
                logging.info('[runner] No epics found for prefix %s in this cycle.', prefix)
            for issue in issues:
                key = issue.get('key')
                if not key:
                    continue
                if key in recently_processed:
                    logging.debug('[runner] Skipping already processed in cache: %s', key)
                    continue

                logging.info('[runner] Processing Epic: %s', key)
                try:
                    process_epic(
                        issue_key=key,
                        language=language,
                        save_to_github=push_to_github,
                        save_locally=True
                    )
                    recently_processed.add(key)
                except Exception as e:
                    logging.error('[runner] Error processing %s: %s', key, str(e))

            time.sleep(sleep_seconds)
        except KeyboardInterrupt:
            logging.info('Runner interrupted. Exiting.')
            break
        except Exception as e:
            logging.error('Runner loop error: %s', str(e))
            time.sleep(sleep_seconds)


