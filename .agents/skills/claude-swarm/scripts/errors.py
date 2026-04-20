#!/usr/bin/env python3
"""Connection error handling for swarm CLI commands."""
import sys
import functools


def handle_connection_error(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            if _is_connection_error(e):
                print(
                    "[swarm] Could not connect to PostgreSQL.\n"
                    "Run the setup flow: /swarm-setup\n"
                    "or set SWARM_PG_DSN in your environment.",
                    file=sys.stderr,
                )
                sys.exit(1)
            raise
    return wrapper


def _is_connection_error(e: Exception) -> bool:
    try:
        import psycopg2
        return isinstance(e, psycopg2.OperationalError)
    except ImportError:
        return False
