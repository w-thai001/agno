#!/usr/bin/env python3
"""
FSA Marathon Data Analysis
Phase 3: Calculate metrics, statistics, and generate insights
"""

import os
import json
import subprocess
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import re

def load_previous_analysis():
    """Load data from previous phases"""
    data = {}

    # Load recovery summary
    recovery_file = '/tmp/fsa_recovery_summary.json'
    if os.path.exists(recovery_file):
        with open(recovery_file, 'r') as f:
            data['recovery'] = json.load(f)

    # Load git analysis
    git_file = '/tmp/fsa_git_analysis.json'
    if os.path.exists(git_file):
        with open(git_file, 'r') as f:
            data['git'] = json.load(f)

    return data

def analyze_commit_patterns(commits):
    """Analyze patterns in commits"""
    print("\n" + "="*70)
    print("ANALYZING COMMIT PATTERNS")
    print("="*70)

    # Group commits by date
    by_date = defaultdict(list)
    by_author = defaultdict(list)
    by_hour = defaultdict(int)

    for commit in commits:
        try:
            date_str = commit['date']
            date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))

            date_key = date_obj.strftime('%Y-%m-%d')
            by_date[date_key].append(commit)

            author = commit['author']
            by_author[author].append(commit)

            hour = date_obj.hour
            by_hour[hour] += 1
        except Exception as e:
            print(f"Warning: Error parsing commit date: {e}")
            continue

    print(f"Commits by {len(by_date)} unique dates")
    print(f"Commits by {len(by_author)} unique authors")

    # Most active dates
    print("\nMost active dates:")
    for date, commits_list in sorted(by_date.items(), key=lambda x: len(x[1]), reverse=True)[:5]:
        print(f"  {date}: {len(commits_list)} commits")

    # Top authors
    print("\nTop authors:")
    for author, commits_list in sorted(by_author.items(), key=lambda x: len(x[1]), reverse=True)[:5]:
        print(f"  {author}: {len(commits_list)} commits")

    # Peak hours
    print("\nPeak commit hours:")
    for hour, count in sorted(by_hour.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"  {hour:02d}:00 - {count} commits")

    return {
        'by_date': {k: len(v) for k, v in by_date.items()},
        'by_author': {k: len(v) for k, v in by_author.items()},
        'by_hour': dict(by_hour)
    }

def analyze_fsa_implementations(fsa_commits):
    """Analyze FSA implementations from commits"""
    print("\n" + "="*70)
    print("ANALYZING FSA IMPLEMENTATIONS")
    print("="*70)

    categories = {
        'feature': [],
        'bugfix': [],
        'enhancement': [],
        'documentation': [],
        'test': [],
        'refactor': [],
        'other': []
    }

    # Categorize FSA commits
    for commit in fsa_commits:
        msg = commit['message'].lower()

        if any(word in msg for word in ['feat', 'feature', 'add', 'implement']):
            categories['feature'].append(commit)
        elif any(word in msg for word in ['fix', 'bug', 'resolve', 'patch']):
            categories['bugfix'].append(commit)
        elif any(word in msg for word in ['enhance', 'improve', 'update', 'optimize']):
            categories['enhancement'].append(commit)
        elif any(word in msg for word in ['doc', 'readme', 'comment']):
            categories['documentation'].append(commit)
        elif any(word in msg for word in ['test', 'spec', 'validation']):
            categories['test'].append(commit)
        elif any(word in msg for word in ['refactor', 'restructure', 'reorganize']):
            categories['refactor'].append(commit)
        else:
            categories['other'].append(commit)

    print("FSA commits by category:")
    for category, commits_list in categories.items():
        if commits_list:
            print(f"  {category.capitalize()}: {len(commits_list)}")

    return {
        'categories': {k: len(v) for k, v in categories.items()},
        'categorized_commits': {k: [c['hash'] for c in v] for k, v in categories.items()}
    }

def calculate_metrics(data):
    """Calculate comprehensive metrics"""
    print("\n" + "="*70)
    print("CALCULATING METRICS")
    print("="*70)

    metrics = {}

    # Git metrics
    if 'git' in data:
        git_data = data['git']

        metrics['total_commits'] = git_data['commits']['total_commits']
        metrics['analyzed_commits'] = len(git_data['commits']['recent_commits'])
        metrics['fsa_commits'] = len(git_data['commits']['fsa_commits'])
        metrics['fsa_percentage'] = (metrics['fsa_commits'] / metrics['analyzed_commits'] * 100) if metrics['analyzed_commits'] > 0 else 0

        metrics['files_changed'] = git_data['changes']['files_changed']
        metrics['insertions'] = git_data['changes']['insertions']
        metrics['deletions'] = git_data['changes']['deletions']
        metrics['net_change'] = metrics['insertions'] - metrics['deletions']

        metrics['current_branch'] = git_data['branches']['current_branch']
        metrics['total_branches'] = len(git_data['branches']['all_branches'])
        metrics['claude_branches'] = len(git_data['branches']['claude_branches'])

        metrics['tracked_files'] = git_data['files']['tracked_files']
        metrics['python_files'] = git_data['files']['file_counts'].get('.py', 0)

    # Calculate productivity metrics
    metrics['lines_per_commit'] = metrics.get('insertions', 0) / max(metrics.get('fsa_commits', 1), 1)
    metrics['files_per_commit'] = metrics.get('files_changed', 0) / max(metrics.get('fsa_commits', 1), 1)

    print("Key Metrics:")
    print(f"  Total Commits: {metrics.get('total_commits', 0)}")
    print(f"  FSA Commits: {metrics.get('fsa_commits', 0)}")
    print(f"  FSA Percentage: {metrics.get('fsa_percentage', 0):.2f}%")
    print(f"  Files Changed: {metrics.get('files_changed', 0)}")
    print(f"  Insertions: {metrics.get('insertions', 0)}")
    print(f"  Deletions: {metrics.get('deletions', 0)}")
    print(f"  Net Change: {metrics.get('net_change', 0)} lines")
    print(f"  Lines per Commit: {metrics.get('lines_per_commit', 0):.1f}")

    return metrics

def analyze_repository_structure():
    """Analyze repository directory structure"""
    print("\n" + "="*70)
    print("ANALYZING REPOSITORY STRUCTURE")
    print("="*70)

    structure = {
        'directories': [],
        'key_files': []
    }

    # Get directory structure
    try:
        result = subprocess.run(
            "find . -maxdepth 2 -type d | grep -v '.git' | head -20",
            shell=True,
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            structure['directories'] = [d.strip() for d in result.stdout.split('\n') if d.strip()]

        # Find key files
        key_patterns = ['README*', 'setup.py', 'requirements.txt', 'pyproject.toml', 'Dockerfile']
        for pattern in key_patterns:
            result = subprocess.run(
                f"find . -maxdepth 2 -name '{pattern}' -type f",
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0 and result.stdout.strip():
                structure['key_files'].extend([f.strip() for f in result.stdout.split('\n') if f.strip()])

    except Exception as e:
        print(f"Warning: Error analyzing structure: {e}")

    print(f"Found {len(structure['directories'])} directories")
    print(f"Found {len(structure['key_files'])} key files")

    return structure

def generate_timeline_data(commits):
    """Generate timeline data for visualization"""
    print("\n" + "="*70)
    print("GENERATING TIMELINE DATA")
    print("="*70)

    timeline = []

    for commit in commits:
        try:
            date_str = commit['date']
            date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))

            timeline.append({
                'date': date_obj.isoformat(),
                'hash': commit['hash'],
                'message': commit['message'],
                'author': commit['author']
            })
        except Exception as e:
            continue

    # Sort by date
    timeline.sort(key=lambda x: x['date'])

    print(f"Generated timeline with {len(timeline)} events")

    return timeline

def main():
    print("="*70)
    print("FSA MARATHON - PHASE 3: DATA ANALYSIS")
    print("="*70)
    print(f"Timestamp: {datetime.now().isoformat()}")

    # Load previous analysis
    data = load_previous_analysis()
    print(f"\nLoaded data from {len(data)} previous phases")

    # Perform analyses
    results = {
        'timestamp': datetime.now().isoformat(),
        'metrics': {},
        'patterns': {},
        'fsa_analysis': {},
        'structure': {},
        'timeline': []
    }

    # Calculate metrics
    results['metrics'] = calculate_metrics(data)

    # Analyze commit patterns
    if 'git' in data and 'commits' in data['git']:
        commits = data['git']['commits']['recent_commits']
        fsa_commits = data['git']['commits']['fsa_commits']

        results['patterns'] = analyze_commit_patterns(commits)
        results['fsa_analysis'] = analyze_fsa_implementations(fsa_commits)
        results['timeline'] = generate_timeline_data(commits)

    # Analyze structure
    results['structure'] = analyze_repository_structure()

    # Save results
    output_file = '/tmp/fsa_data_analysis.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print("\n" + "="*70)
    print("PHASE 3 SUMMARY")
    print("="*70)
    print(f"Analysis completed successfully")
    print(f"Results saved to: {output_file}")
    print()
    print("Key Findings:")
    print(f"  Repository Size: {results['metrics'].get('total_commits', 0)} commits")
    print(f"  Code Base: {results['metrics'].get('python_files', 0)} Python files")
    print(f"  Recent Activity: {results['metrics'].get('files_changed', 0)} files modified")
    print(f"  Code Growth: +{results['metrics'].get('net_change', 0)} net lines")

    return results

if __name__ == '__main__':
    analysis = main()
