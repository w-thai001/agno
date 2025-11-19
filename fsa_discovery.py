#!/usr/bin/env python3
"""
FSA Discovery and Cataloging Script
Discovers, analyzes, and catalogs all FSA implementations in the repository
"""

import subprocess
import json
import re
import time
from pathlib import Path
from typing import List, Dict, Set
from collections import defaultdict

# Rate limit delay between operations
RATE_LIMIT_DELAY = 3.0

def run_git_command(cmd: List[str]) -> str:
    """Run a git command and return output"""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running command {' '.join(cmd)}: {e}")
        return ""

def discover_fsa_files() -> List[str]:
    """Discover all FSA-related files using git commands"""
    print("Phase 1: Discovering FSA files...")

    # Get all files in the repository
    all_files = run_git_command(['git', 'ls-files']).split('\n')
    print(f"Total files in repository: {len(all_files)}")

    # Filter for FSA-related files by name/path
    fsa_files = []
    fsa_patterns = [
        r'fsa',
        r'finite.*state',
        r'state.*machine',
        r'automaton',
        r'workflow',
        r'agent.*flow'
    ]

    for file in all_files:
        file_lower = file.lower()
        if any(re.search(pattern, file_lower) for pattern in fsa_patterns):
            if file.endswith(('.py', '.ts', '.js', '.md', '.json', '.txt')):
                fsa_files.append(file)

    print(f"Found {len(fsa_files)} FSA-related files by name/path")

    # Also search for files containing FSA-related keywords in content
    print("\nSearching for FSA-related content in Python/TypeScript/JavaScript files...")
    time.sleep(RATE_LIMIT_DELAY)

    # Get all code files
    code_files = [f for f in all_files if f.endswith(('.py', '.ts', '.js'))]

    # Search for FSA-related content using git grep
    fsa_content_keywords = [
        'FSA',
        'FiniteStateAutomaton',
        'StateMachine',
        'AgentFlow',
        'WorkflowState'
    ]

    content_fsa_files = set()
    for keyword in fsa_content_keywords:
        time.sleep(RATE_LIMIT_DELAY)
        grep_output = run_git_command(['git', 'grep', '-l', keyword, '--', '*.py', '*.ts', '*.js'])
        if grep_output:
            content_fsa_files.update(grep_output.split('\n'))
            print(f"  Keyword '{keyword}': {len(grep_output.split())} files")

    # Combine both lists
    all_fsa_files = list(set(fsa_files) | content_fsa_files)
    print(f"\nTotal FSA-related files discovered: {len(all_fsa_files)}")

    return sorted(all_fsa_files)

def get_file_language(filepath: str) -> str:
    """Determine the language of a file"""
    ext = Path(filepath).suffix.lower()
    mapping = {
        '.py': 'Python',
        '.ts': 'TypeScript',
        '.js': 'JavaScript',
        '.md': 'Markdown',
        '.json': 'JSON',
        '.txt': 'Text'
    }
    return mapping.get(ext, 'Unknown')

def analyze_file(filepath: str) -> Dict:
    """Analyze a single file for FSA-related information"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        lines = content.split('\n')
        loc = len(lines)

        # Extract metadata from file header
        description = ""
        class_names = []
        function_names = []
        dependencies = []

        # Look for docstrings/comments in first 20 lines
        header_lines = lines[:20]
        for line in header_lines:
            if '"""' in line or "'''" in line or line.strip().startswith('#'):
                cleaned = line.strip().strip('#').strip('"').strip("'").strip()
                if cleaned and len(cleaned) > 10:
                    description = cleaned
                    break

        # Find class definitions
        class_pattern = r'class\s+(\w+)'
        class_names = re.findall(class_pattern, content)

        # Find function definitions
        func_patterns = [
            r'def\s+(\w+)',  # Python
            r'function\s+(\w+)',  # JavaScript
            r'async\s+def\s+(\w+)',  # Python async
            r'async\s+function\s+(\w+)',  # JavaScript async
        ]
        for pattern in func_patterns:
            function_names.extend(re.findall(pattern, content))

        # Find imports/dependencies
        import_patterns = [
            r'from\s+([\w.]+)\s+import',  # Python from import
            r'import\s+([\w.]+)',  # Python/JavaScript import
            r'require\(["\']([^"\']+)["\']\)',  # JavaScript require
        ]
        for pattern in import_patterns:
            dependencies.extend(re.findall(pattern, content))

        # Categorize by domain
        domain = categorize_domain(filepath, content)

        # Estimate complexity
        complexity = estimate_complexity(content, loc)

        return {
            'filepath': filepath,
            'filename': Path(filepath).name,
            'language': get_file_language(filepath),
            'description': description or f"FSA implementation in {Path(filepath).name}",
            'domain': domain,
            'loc': loc,
            'classes': list(set(class_names))[:10],  # Limit to 10
            'functions': list(set(function_names))[:20],  # Limit to 20
            'dependencies': list(set(dependencies))[:15],  # Limit to 15
            'complexity': complexity
        }
    except Exception as e:
        print(f"Error analyzing {filepath}: {e}")
        return None

def categorize_domain(filepath: str, content: str) -> str:
    """Categorize FSA by domain"""
    filepath_lower = filepath.lower()
    content_lower = content.lower()

    domain_keywords = {
        'messaging': ['message', 'chat', 'conversation', 'sms', 'email'],
        'concurrency': ['async', 'concurrent', 'parallel', 'thread', 'queue'],
        'networking': ['http', 'api', 'request', 'response', 'socket'],
        'workflow': ['workflow', 'pipeline', 'orchestration', 'task'],
        'agent': ['agent', 'llm', 'ai', 'model'],
        'data_processing': ['data', 'processing', 'transform', 'etl'],
        'testing': ['test', 'mock', 'fixture', 'pytest'],
        'documentation': ['doc', 'readme', 'guide', 'example'],
        'utility': ['util', 'helper', 'common', 'base'],
    }

    for domain, keywords in domain_keywords.items():
        if any(keyword in filepath_lower or keyword in content_lower for keyword in keywords):
            return domain

    return 'general'

def estimate_complexity(content: str, loc: int) -> str:
    """Estimate complexity based on various metrics"""
    # Count control flow statements
    control_flow = len(re.findall(r'\b(if|else|elif|for|while|try|except|match|case)\b', content))

    # Count function/method definitions
    functions = len(re.findall(r'\b(def|function|async)\s+\w+', content))

    # Calculate complexity score
    score = (control_flow * 2) + (functions * 3) + (loc / 10)

    if score < 50:
        return 'low'
    elif score < 200:
        return 'medium'
    else:
        return 'high'

def build_relationship_graph(catalog: List[Dict]) -> Dict[str, List[str]]:
    """Build a graph of FSA relationships based on dependencies"""
    graph = defaultdict(list)

    # Create a mapping of module names to filepaths
    module_to_file = {}
    for item in catalog:
        if item:
            module_name = Path(item['filepath']).stem
            module_to_file[module_name] = item['filepath']

    # Build relationships
    for item in catalog:
        if not item:
            continue

        filepath = item['filepath']
        for dep in item['dependencies']:
            # Clean up dependency name
            dep_clean = dep.split('.')[0]
            if dep_clean in module_to_file:
                graph[filepath].append(module_to_file[dep_clean])

    return dict(graph)

def generate_statistics(catalog: List[Dict]) -> Dict:
    """Generate statistics from the catalog"""
    stats = {
        'total_count': len([c for c in catalog if c]),
        'by_language': defaultdict(int),
        'by_domain': defaultdict(int),
        'by_complexity': defaultdict(int),
        'total_loc': 0,
        'avg_loc': 0,
    }

    valid_items = [c for c in catalog if c]

    for item in valid_items:
        stats['by_language'][item['language']] += 1
        stats['by_domain'][item['domain']] += 1
        stats['by_complexity'][item['complexity']] += 1
        stats['total_loc'] += item['loc']

    if valid_items:
        stats['avg_loc'] = stats['total_loc'] / len(valid_items)

    # Convert defaultdicts to regular dicts
    stats['by_language'] = dict(stats['by_language'])
    stats['by_domain'] = dict(stats['by_domain'])
    stats['by_complexity'] = dict(stats['by_complexity'])

    return stats

def main():
    """Main execution function"""
    print("=" * 80)
    print("FSA Discovery and Cataloging Script")
    print("=" * 80)

    # Phase 1: Discovery
    fsa_files = discover_fsa_files()

    if not fsa_files:
        print("No FSA files found!")
        return

    print("\n" + "=" * 80)
    print("Phase 2: Analyzing FSA implementations...")
    print("=" * 80)

    catalog = []
    for i, filepath in enumerate(fsa_files, 1):
        print(f"\nAnalyzing [{i}/{len(fsa_files)}]: {filepath}")

        # Rate limit compliance
        if i % 10 == 0:
            print(f"  [Rate limit: waiting {RATE_LIMIT_DELAY}s...]")
            time.sleep(RATE_LIMIT_DELAY)

        analysis = analyze_file(filepath)
        if analysis:
            catalog.append(analysis)
            print(f"  Language: {analysis['language']}, Domain: {analysis['domain']}, "
                  f"LOC: {analysis['loc']}, Complexity: {analysis['complexity']}")

    print("\n" + "=" * 80)
    print("Phase 3: Generating catalog and documentation...")
    print("=" * 80)

    # Generate statistics
    stats = generate_statistics(catalog)

    # Build relationship graph
    relationships = build_relationship_graph(catalog)

    # Create final catalog structure
    final_catalog = {
        'metadata': {
            'generated_at': time.strftime('%Y-%m-%d %H:%M:%S'),
            'repository': 'w-thai001/agno',
            'total_files_analyzed': len(fsa_files),
        },
        'statistics': stats,
        'catalog': sorted([c for c in catalog if c], key=lambda x: x['filepath']),
        'relationships': relationships
    }

    # Save catalog to JSON
    catalog_path = 'fsa_catalog.json'
    with open(catalog_path, 'w', encoding='utf-8') as f:
        json.dump(final_catalog, f, indent=2)

    print(f"\n✓ Catalog saved to: {catalog_path}")
    print(f"\nStatistics:")
    print(f"  Total FSA files: {stats['total_count']}")
    print(f"  Total LOC: {stats['total_loc']:,}")
    print(f"  Average LOC: {stats['avg_loc']:.1f}")
    print(f"\n  By Language:")
    for lang, count in sorted(stats['by_language'].items()):
        print(f"    {lang}: {count}")
    print(f"\n  By Domain:")
    for domain, count in sorted(stats['by_domain'].items()):
        print(f"    {domain}: {count}")
    print(f"\n  By Complexity:")
    for complexity, count in sorted(stats['by_complexity'].items()):
        print(f"    {complexity}: {count}")

    return final_catalog

if __name__ == '__main__':
    main()
