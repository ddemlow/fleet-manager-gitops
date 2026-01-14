#!/usr/bin/env python3
"""
Monitor deployment releases and report their results.

This file is a small compatibility wrapper. The importable implementation lives
in `monitor_deployment_releases.py` so that other scripts (like `deploy.py`) can
import it.
"""

from monitor_deployment_releases import main

if __name__ == "__main__":
    main()
