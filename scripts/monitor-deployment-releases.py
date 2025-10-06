#!/usr/bin/env python3
"""
Monitor deployment releases and report their results
"""

import os
import sys
import time
import requests
import json
from typing import Dict, List, Optional, Any
from datetime import datetime

class DeploymentReleaseMonitor:
    def __init__(self):
        self.fm_api_key = os.getenv('SC_FM_APIKEY')
        self.fm_api_url = os.getenv('FLEET_MANAGER_API_URL', 'https://api.scalecomputing.com/api/v2')
        
        if not self.fm_api_key:
            print("❌ SC_FM_APIKEY environment variable is required")
            sys.exit(1)
            
        self.headers = {
            'Authorization': f'Bearer {self.fm_api_key}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

    def get_deployment_releases(self, deployment_id: str) -> List[Dict[str, Any]]:
        """Get all releases for a specific deployment"""
        try:
            response = requests.get(
                f"{self.fm_api_url}/deployments/{deployment_id}/releases",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ Error getting deployment releases for {deployment_id}: {e}")
            return []

    def get_deployment_details(self, deployment_id: str) -> Optional[Dict[str, Any]]:
        """Get deployment details"""
        try:
            response = requests.get(
                f"{self.fm_api_url}/deployments/{deployment_id}",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ Error getting deployment details for {deployment_id}: {e}")
            return None

    def get_release_jobs(self, release_id: str) -> List[Dict[str, Any]]:
        """Get jobs for a specific release"""
        try:
            response = requests.get(
                f"{self.fm_api_url}/deployment-releases/{release_id}/jobs",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ Error getting release jobs for {release_id}: {e}")
            return []

    def format_status(self, status: str, count: int = None) -> str:
        """Format status with emoji and count"""
        status_emojis = {
            'Success': '✅',
            'Running': '🔄',
            'Failed': '❌',
            'Pending': '⏳',
            'Created': '📝',
            'Done': '✅'
        }
        
        emoji = status_emojis.get(status, '❓')
        if count is not None:
            return f"{emoji} {count} {status}"
        return f"{emoji} {status}"

    def format_timestamp(self, timestamp: str) -> str:
        """Format timestamp for display"""
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d %H:%M:%S UTC')
        except:
            return timestamp

    def monitor_deployment(self, deployment_id: str, timeout_minutes: int = 30, check_interval: int = 30) -> Dict[str, Any]:
        """Monitor a deployment until completion or timeout"""
        print(f"🔍 Monitoring deployment: {deployment_id}")
        print(f"⏱️  Timeout: {timeout_minutes} minutes, Check interval: {check_interval} seconds")
        
        start_time = time.time()
        timeout_seconds = timeout_minutes * 60
        
        # Get initial deployment details
        deployment = self.get_deployment_details(deployment_id)
        if not deployment:
            return {'status': 'error', 'message': 'Failed to get deployment details'}
        
        print(f"📋 Deployment: {deployment.get('name', 'Unknown')}")
        print(f"🎯 Cluster Group: {deployment.get('clusterGroupId', 'Unknown')}")
        
        last_release_count = 0
        
        while time.time() - start_time < timeout_seconds:
            # Get current releases
            releases = self.get_deployment_releases(deployment_id)
            
            if len(releases) > last_release_count:
                print(f"🆕 New release detected! Total releases: {len(releases)}")
                last_release_count = len(releases)
            
            # Check the latest release
            if releases:
                latest_release = releases[-1]  # Assuming releases are ordered by creation time
                release_id = latest_release.get('id')
                release_status = latest_release.get('status', 'Unknown')
                created_at = latest_release.get('createdAt', '')
                
                print(f"📊 Latest Release: {release_id}")
                print(f"📈 Status: {self.format_status(release_status)}")
                print(f"🕐 Created: {self.format_timestamp(created_at)}")
                
                # Get jobs for this release
                jobs = self.get_release_jobs(release_id)
                if jobs:
                    # Count job statuses
                    job_statuses = {}
                    for job in jobs:
                        status = job.get('status', 'Unknown')
                        job_statuses[status] = job_statuses.get(status, 0) + 1
                    
                    print(f"🔧 Jobs ({len(jobs)} total):")
                    for status, count in job_statuses.items():
                        print(f"   {self.format_status(status, count)}")
                
                # Check if deployment is complete
                if release_status in ['Success', 'Failed']:
                    print(f"🏁 Deployment completed with status: {self.format_status(release_status)}")
                    
                    # Compile final report
                    report = {
                        'deployment_id': deployment_id,
                        'deployment_name': deployment.get('name', 'Unknown'),
                        'final_status': release_status,
                        'total_releases': len(releases),
                        'latest_release_id': release_id,
                        'jobs': jobs,
                        'job_statuses': job_statuses,
                        'duration_minutes': round((time.time() - start_time) / 60, 2),
                        'completed_at': datetime.utcnow().isoformat() + 'Z'
                    }
                    
                    return report
                
                elif release_status in ['Running', 'Pending', 'Created']:
                    print(f"⏳ Deployment still in progress...")
            
            else:
                print("⏳ No releases found yet, waiting...")
            
            # Wait before next check
            print(f"💤 Waiting {check_interval} seconds before next check...")
            time.sleep(check_interval)
        
        # Timeout reached
        print(f"⏰ Timeout reached ({timeout_minutes} minutes)")
        return {
            'status': 'timeout',
            'deployment_id': deployment_id,
            'timeout_minutes': timeout_minutes,
            'releases': releases,
            'message': f'Deployment monitoring timed out after {timeout_minutes} minutes'
        }

    def report_deployment_results(self, deployment_ids: List[str], timeout_minutes: int = 30) -> Dict[str, Any]:
        """Monitor multiple deployments and report results"""
        results = {}
        
        print(f"🚀 Starting deployment monitoring for {len(deployment_ids)} deployments")
        print(f"⏱️  Timeout per deployment: {timeout_minutes} minutes")
        
        for deployment_id in deployment_ids:
            print(f"\n{'='*60}")
            result = self.monitor_deployment(deployment_id, timeout_minutes)
            results[deployment_id] = result
            print(f"{'='*60}")
        
        # Generate summary
        print(f"\n📊 DEPLOYMENT MONITORING SUMMARY")
        print(f"{'='*60}")
        
        success_count = 0
        failed_count = 0
        timeout_count = 0
        error_count = 0
        
        for deployment_id, result in results.items():
            deployment_name = result.get('deployment_name', 'Unknown')
            status = result.get('final_status', result.get('status', 'Unknown'))
            
            print(f"📋 {deployment_name} ({deployment_id[:8]}...): {self.format_status(status)}")
            
            if status == 'Success':
                success_count += 1
                duration = result.get('duration_minutes', 0)
                print(f"   ⏱️  Duration: {duration} minutes")
                if 'job_statuses' in result:
                    for job_status, count in result['job_statuses'].items():
                        print(f"   🔧 {self.format_status(job_status, count)}")
            
            elif status == 'Failed':
                failed_count += 1
            elif status == 'timeout':
                timeout_count += 1
            elif status == 'error':
                error_count += 1
        
        print(f"\n📈 TOTALS:")
        print(f"   ✅ Successful: {success_count}")
        print(f"   ❌ Failed: {failed_count}")
        print(f"   ⏰ Timeout: {timeout_count}")
        print(f"   ❓ Error: {error_count}")
        
        return {
            'summary': {
                'total': len(deployment_ids),
                'success': success_count,
                'failed': failed_count,
                'timeout': timeout_count,
                'error': error_count
            },
            'results': results
        }

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Monitor deployment releases')
    parser.add_argument('deployment_ids', nargs='+', help='Deployment IDs to monitor')
    parser.add_argument('--timeout', type=int, default=30, help='Timeout in minutes (default: 30)')
    parser.add_argument('--interval', type=int, default=30, help='Check interval in seconds (default: 30)')
    parser.add_argument('--output', help='Output file for results (JSON)')
    
    args = parser.parse_args()
    
    monitor = DeploymentReleaseMonitor()
    
    # Override check interval if specified
    if args.interval:
        monitor.check_interval = args.interval
    
    # Monitor deployments
    results = monitor.report_deployment_results(args.deployment_ids, args.timeout)
    
    # Save results to file if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"💾 Results saved to: {args.output}")
    
    # Exit with appropriate code
    if results['summary']['failed'] > 0 or results['summary']['error'] > 0:
        sys.exit(1)
    elif results['summary']['timeout'] > 0:
        sys.exit(2)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()
