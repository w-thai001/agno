#!/usr/bin/env python3
"""
FSA Marathon Git Repository Analysis
Phase 2: Analyze commits, changes, and FSA implementations
"""

import os
import subprocess
import json
import re
from datetime import datetime, timedelta
from collections import defaultdict

def run_git_command(cmd, cwd=None):
    """Execute git command and return output"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd or os.getcwd(),
            capture_output=True,
            text=True,
            timeout=30
        )
        return {
            'success': result.returncode == 0,
            'stdout': result.stdout.strip(),
            'stderr': result.stderr.strip(),
            'returncode': result.returncode
        }
    except subprocess.TimeoutExpired:
        return {'success': False, 'stdout': '', 'stderr': 'Command timeout', 'returncode': -1}
    except Exception as e:
        return {'success': False, 'stdout': '', 'stderr': str(e), 'returncode': -1}

def analyze_commits(since_date=None, until_date=None):
    """Analyze git commits in date range"""
    print("\n" + "="*70)
    print("ANALYZING GIT COMMITS")
    print("="*70)

    # Get commit count
    cmd = "git rev-list --count HEAD"
    result = run_git_command(cmd)
    total_commits = int(result['stdout']) if result['success'] else 0
    print(f"Total commits in repository: {total_commits}")

    # Get recent commits (last 100)
    cmd = "git log --oneline -100 --format='%H|%an|%ae|%ai|%s'"
    result = run_git_command(cmd)

    commits = []
    if result['success']:
        for line in result['stdout'].split('\n'):
            if line.strip():
                parts = line.split('|')
                if len(parts) >= 5:
                    commits.append({
                        'hash': parts[0],
                        'author': parts[1],
                        'email': parts[2],
                        'date': parts[3],
                        'message': '|'.join(parts[4:])
                    })

    print(f"Analyzed last {len(commits)} commits")

    # Filter FSA-related commits
    fsa_keywords = ['fsa', 'assessment', 'marathon', 'agno', 'assist', 'claude']
    fsa_commits = []

    for commit in commits:
        msg_lower = commit['message'].lower()
        if any(keyword in msg_lower for keyword in fsa_keywords):
            fsa_commits.append(commit)

    print(f"FSA-related commits: {len(fsa_commits)}")

    return {
        'total_commits': total_commits,
        'recent_commits': commits,
        'fsa_commits': fsa_commits
    }

def analyze_changes():
    """Analyze file changes in repository"""
    print("\n" + "="*70)
    print("ANALYZING FILE CHANGES")
    print("="*70)

    # Get diff stats for last 50 commits
    cmd = "git diff --stat HEAD~50..HEAD 2>/dev/null || git diff --stat --root HEAD"
    result = run_git_command(cmd)

    changes = {
        'files_changed': 0,
        'insertions': 0,
        'deletions': 0,
        'details': result['stdout'] if result['success'] else ''
    }

    if result['success']:
        # Parse summary line: "X files changed, Y insertions(+), Z deletions(-)"
        summary_match = re.search(r'(\d+) files? changed', result['stdout'])
        if summary_match:
            changes['files_changed'] = int(summary_match.group(1))

        insertion_match = re.search(r'(\d+) insertions?', result['stdout'])
        if insertion_match:
            changes['insertions'] = int(insertion_match.group(1))

        deletion_match = re.search(r'(\d+) deletions?', result['stdout'])
        if deletion_match:
            changes['deletions'] = int(deletion_match.group(1))

    print(f"Files changed: {changes['files_changed']}")
    print(f"Insertions: {changes['insertions']}")
    print(f"Deletions: {changes['deletions']}")

    return changes

def analyze_branches():
    """Analyze git branches"""
    print("\n" + "="*70)
    print("ANALYZING BRANCHES")
    print("="*70)

    # Get current branch
    cmd = "git branch --show-current"
    result = run_git_command(cmd)
    current_branch = result['stdout'] if result['success'] else 'unknown'
    print(f"Current branch: {current_branch}")

    # Get all branches
    cmd = "git branch -a"
    result = run_git_command(cmd)
    all_branches = result['stdout'].split('\n') if result['success'] else []

    # Filter Claude-related branches
    claude_branches = [b.strip() for b in all_branches if 'claude' in b.lower()]
    print(f"Claude-related branches: {len(claude_branches)}")

    return {
        'current_branch': current_branch,
        'all_branches': [b.strip() for b in all_branches],
        'claude_branches': claude_branches
    }

def analyze_file_types():
    """Analyze file types in repository"""
    print("\n" + "="*70)
    print("ANALYZING FILE TYPES")
    print("="*70)

    cmd = "git ls-files | grep -E '\\.py$|\\.md$|\\.json$|\\.txt$|\\.yaml$|\\.yml$' | wc -l"
    result = run_git_command(cmd)
    tracked_files = int(result['stdout']) if result['success'] else 0

    # Count by extension
    file_counts = defaultdict(int)
    cmd = "git ls-files"
    result = run_git_command(cmd)

    if result['success']:
        for filepath in result['stdout'].split('\n'):
            if filepath.strip():
                ext = os.path.splitext(filepath)[1]
                if ext:
                    file_counts[ext] += 1
                else:
                    file_counts['[no extension]'] += 1

    print(f"Total tracked files: {tracked_files}")
    print("Top file types:")
    for ext, count in sorted(file_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {ext}: {count}")

    return {
        'tracked_files': tracked_files,
        'file_counts': dict(file_counts)
    }

def main():
    print("="*70)
    print("FSA MARATHON - PHASE 2: GIT REPOSITORY ANALYSIS")
    print("="*70)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Working Directory: {os.getcwd()}")

    # Verify we're in a git repository
    result = run_git_command("git rev-parse --git-dir")
    if not result['success']:
        print("\n✗ ERROR: Not a git repository!")
        return None

    print("✓ Git repository confirmed")

    # Run analyses
    commits_data = analyze_commits()
    changes_data = analyze_changes()
    branches_data = analyze_branches()
    files_data = analyze_file_types()

    # Compile results
    analysis_results = {
        'timestamp': datetime.now().isoformat(),
        'working_directory': os.getcwd(),
        'commits': commits_data,
        'changes': changes_data,
        'branches': branches_data,
        'files': files_data
    }

    # Save results
    output_file = '/tmp/fsa_git_analysis.json'
    with open(output_file, 'w') as f:
        json.dump(analysis_results, f, indent=2)

    print("\n" + "="*70)
    print("PHASE 2 SUMMARY")
    print("="*70)
    print(f"Total commits: {commits_data['total_commits']}")
    print(f"FSA-related commits: {len(commits_data['fsa_commits'])}")
    print(f"Current branch: {branches_data['current_branch']}")
    print(f"Files changed (last 50 commits): {changes_data['files_changed']}")
    print(f"Analysis saved to: {output_file}")
    print()

    # Show recent FSA commits
    if commits_data['fsa_commits']:
        print("Recent FSA-related commits:")
        for commit in commits_data['fsa_commits'][:10]:
            print(f"  {commit['hash'][:8]} - {commit['message'][:60]}")
            print(f"    {commit['date']} by {commit['author']}")

    return analysis_results

if __name__ == '__main__':
    results = main()
