#!/usr/bin/env python3
"""
Monitor deployment releases and report their results.

Note: This module is intentionally importable (underscored filename) so it can be
used by `scripts/deploy.py` when MONITOR_DEPLOYMENTS=true.
"""

import json
import os
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests


class DeploymentReleaseMonitor:
    def __init__(self):
        self.fm_api_key = os.getenv("SC_FM_APIKEY")
        self.fm_api_url = os.getenv("FLEET_MANAGER_API_URL", "https://api.scalecomputing.com/api/v2")

        if not self.fm_api_key:
            raise ValueError("SC_FM_APIKEY environment variable is required")

        # Match the auth style used by scripts/deploy.py (server-to-server API key header).
        self.headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "api-key": self.fm_api_key,
            "user-agent": "fleet-manager-gitops/2.0",
        }

    def get_deployment_releases(self, deployment_id: str) -> List[Dict[str, Any]]:
        """Get all releases for a specific deployment."""
        try:
            response = requests.get(
                f"{self.fm_api_url}/deployments/{deployment_id}/releases",
                headers=self.headers,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            # API responses vary; accept either a list or an {items: [...]} shape.
            if isinstance(data, dict) and isinstance(data.get("items"), list):
                return data["items"]
            return data if isinstance(data, list) else []
        except Exception as e:
            print(f"❌ Error getting deployment releases for {deployment_id}: {e}")
            return []

    def get_deployment_details(self, deployment_id: str) -> Optional[Dict[str, Any]]:
        """Get deployment details."""
        try:
            response = requests.get(
                f"{self.fm_api_url}/deployments/{deployment_id}",
                headers=self.headers,
                timeout=30,
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ Error getting deployment details for {deployment_id}: {e}")
            return None

    def get_release_jobs(self, release_id: str) -> List[Dict[str, Any]]:
        """Get jobs for a specific release."""
        try:
            response = requests.get(
                f"{self.fm_api_url}/deployment-releases/{release_id}/jobs",
                headers=self.headers,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            if isinstance(data, dict) and isinstance(data.get("items"), list):
                return data["items"]
            return data if isinstance(data, list) else []
        except Exception as e:
            print(f"❌ Error getting release jobs for {release_id}: {e}")
            return []

    @staticmethod
    def format_status(status: str, count: int | None = None) -> str:
        """Format status with emoji and count."""
        status_emojis = {
            "Success": "✅",
            "Running": "🔄",
            "Failed": "❌",
            "Pending": "⏳",
            "Created": "📝",
            "Done": "✅",
        }
        emoji = status_emojis.get(status, "❓")
        return f"{emoji} {count} {status}" if count is not None else f"{emoji} {status}"

    @staticmethod
    def format_timestamp(timestamp: str) -> str:
        """Format timestamp for display."""
        try:
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
        except Exception:
            return timestamp

    def monitor_deployment(
        self,
        deployment_id: str,
        timeout_minutes: int = 30,
        check_interval: int = 30,
    ) -> Dict[str, Any]:
        """Monitor a deployment until completion or timeout."""
        print(f"🔍 Monitoring deployment: {deployment_id}")
        print(f"⏱️  Timeout: {timeout_minutes} minutes, Check interval: {check_interval} seconds")

        start_time = time.time()
        timeout_seconds = timeout_minutes * 60

        deployment = self.get_deployment_details(deployment_id)
        if not deployment:
            return {"status": "error", "message": "Failed to get deployment details"}

        print(f"📋 Deployment: {deployment.get('name', 'Unknown')}")

        last_release_count = 0
        releases: List[Dict[str, Any]] = []

        while time.time() - start_time < timeout_seconds:
            releases = self.get_deployment_releases(deployment_id)

            if len(releases) > last_release_count:
                print(f"🆕 New release detected! Total releases: {len(releases)}")
                last_release_count = len(releases)

            if releases:
                latest_release = releases[-1]
                release_id = latest_release.get("id")
                release_status = latest_release.get("status", "Unknown")
                created_at = latest_release.get("createdAt", "")

                print(f"📊 Latest Release: {release_id}")
                print(f"📈 Status: {self.format_status(release_status)}")
                if created_at:
                    print(f"🕐 Created: {self.format_timestamp(created_at)}")

                jobs = self.get_release_jobs(release_id) if release_id else []
                job_statuses: Dict[str, int] = {}
                if jobs:
                    for job in jobs:
                        status = job.get("status", "Unknown")
                        job_statuses[status] = job_statuses.get(status, 0) + 1

                    print(f"🔧 Jobs ({len(jobs)} total):")
                    for status, count in job_statuses.items():
                        print(f"   {self.format_status(status, count)}")

                if release_status in ["Success", "Failed"]:
                    print(f"🏁 Deployment completed with status: {self.format_status(release_status)}")
                    return {
                        "deployment_id": deployment_id,
                        "deployment_name": deployment.get("name", "Unknown"),
                        "final_status": release_status,
                        "total_releases": len(releases),
                        "latest_release_id": release_id,
                        "jobs": jobs,
                        "job_statuses": job_statuses,
                        "duration_minutes": round((time.time() - start_time) / 60, 2),
                        "completed_at": datetime.utcnow().isoformat() + "Z",
                    }

                if release_status in ["Running", "Pending", "Created"]:
                    print("⏳ Deployment still in progress...")
            else:
                print("⏳ No releases found yet, waiting...")

            time.sleep(check_interval)

        print(f"⏰ Timeout reached ({timeout_minutes} minutes)")
        return {
            "status": "timeout",
            "deployment_id": deployment_id,
            "timeout_minutes": timeout_minutes,
            "releases": releases,
            "message": f"Deployment monitoring timed out after {timeout_minutes} minutes",
        }

    def report_deployment_results(
        self,
        deployment_ids: List[str],
        timeout_minutes: int = 30,
        check_interval: int = 30,
    ) -> Dict[str, Any]:
        """Monitor multiple deployments and report results."""
        results: Dict[str, Any] = {}

        print(f"🚀 Starting deployment monitoring for {len(deployment_ids)} deployments")
        print(f"⏱️  Timeout per deployment: {timeout_minutes} minutes")

        for deployment_id in deployment_ids:
            print(f"\n{'=' * 60}")
            result = self.monitor_deployment(deployment_id, timeout_minutes, check_interval)
            results[deployment_id] = result
            print(f"{'=' * 60}")

        success_count = 0
        failed_count = 0
        timeout_count = 0
        error_count = 0

        print("\n📊 DEPLOYMENT MONITORING SUMMARY")
        print(f"{'=' * 60}")
        for deployment_id, result in results.items():
            deployment_name = result.get("deployment_name", "Unknown")
            status = result.get("final_status", result.get("status", "Unknown"))

            print(f"📋 {deployment_name} ({deployment_id[:8]}...): {self.format_status(status)}")

            if status == "Success":
                success_count += 1
            elif status == "Failed":
                failed_count += 1
            elif status == "timeout":
                timeout_count += 1
            elif status == "error":
                error_count += 1

        print("\n📈 TOTALS:")
        print(f"   ✅ Successful: {success_count}")
        print(f"   ❌ Failed: {failed_count}")
        print(f"   ⏰ Timeout: {timeout_count}")
        print(f"   ❓ Error: {error_count}")

        return {
            "summary": {
                "total": len(deployment_ids),
                "success": success_count,
                "failed": failed_count,
                "timeout": timeout_count,
                "error": error_count,
            },
            "results": results,
        }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Monitor deployment releases")
    parser.add_argument("deployment_ids", nargs="+", help="Deployment IDs to monitor")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout in minutes (default: 30)")
    parser.add_argument("--interval", type=int, default=30, help="Check interval in seconds (default: 30)")
    parser.add_argument("--output", help="Output file for results (JSON)")

    args = parser.parse_args()

    try:
        monitor = DeploymentReleaseMonitor()
        results = monitor.report_deployment_results(args.deployment_ids, args.timeout, args.interval)
    except Exception as e:
        print(f"❌ Monitoring failed: {e}")
        sys.exit(1)

    if args.output:
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2)
        print(f"💾 Results saved to: {args.output}")

    if results["summary"]["failed"] > 0 or results["summary"]["error"] > 0:
        sys.exit(1)
    if results["summary"]["timeout"] > 0:
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()

