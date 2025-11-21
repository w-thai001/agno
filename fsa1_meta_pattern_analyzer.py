#!/usr/bin/env python3
"""
FSA-1: Meta-Pattern Analyzer

This module analyzes execution logs to identify top-performing patterns and generate
optimization recommendations. It uses PowerShell subprocesses for file operations
and provides comprehensive statistical analysis of pattern performance.

Author: Agno Team
License: MIT
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from statistics import mean, stdev
from collections import defaultdict
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class PatternStatistics:
    """Statistical metrics for a pattern's performance."""
    pattern_id: str
    execution_count: int
    mean_lq_score: float
    max_lq_score: float
    min_lq_score: float
    std_dev_lq_score: float
    success_rate: float
    total_successes: int
    total_failures: int
    avg_execution_time: float


@dataclass
class Recommendation:
    """Optimization recommendation based on pattern analysis."""
    priority: str  # HIGH, MEDIUM, LOW
    pattern_id: str
    recommendation_type: str
    description: str
    expected_impact: str
    metrics: Dict[str, Any]


class PowerShellExecutor:
    """Handles PowerShell subprocess execution with timeout and error handling."""

    def __init__(self, timeout: int = 30):
        """
        Initialize PowerShell executor.

        Args:
            timeout: Maximum time in seconds to wait for command completion
        """
        self.timeout = timeout
        self.platform = sys.platform
        self.use_fallback = False
        self._check_powershell_availability()

    def _check_powershell_availability(self):
        """Check if PowerShell is available on the system."""
        try:
            ps_exe = 'powershell' if self.platform.startswith('win') else 'pwsh'
            subprocess.run(
                [ps_exe, '-Command', 'echo test'],
                capture_output=True,
                timeout=5,
                check=True
            )
            logger.info(f"PowerShell ({ps_exe}) is available")
        except (FileNotFoundError, subprocess.SubprocessError):
            logger.warning("PowerShell not available, using fallback shell commands")
            self.use_fallback = True

    def _execute_fallback(self, powershell_command: str) -> str:
        """
        Execute equivalent bash command when PowerShell is not available.

        Args:
            powershell_command: Original PowerShell command

        Returns:
            Command output as string
        """
        # Convert PowerShell Get-ChildItem commands to find/ls equivalents
        if 'Get-ChildItem' in powershell_command:
            # Extract path and filter from PowerShell command
            import re

            path_match = re.search(r"-Path\s+'([^']+)'", powershell_command)
            filter_match = re.search(r"-Filter\s+'([^']+)'", powershell_command)

            path = path_match.group(1) if path_match else '.'
            filter_pattern = filter_match.group(1) if filter_match else '*'

            # Use find command for recursive search
            if '-Recurse' in powershell_command:
                bash_command = f"find {path} -type f -name '{filter_pattern}'"
            else:
                bash_command = f"find {path} -maxdepth 1 -type f -name '{filter_pattern}'"

        elif 'Get-Content' in powershell_command:
            # Extract path from PowerShell command
            import re
            path_match = re.search(r"-Path\s+'([^']+)'", powershell_command)

            if path_match:
                path = path_match.group(1)
                bash_command = f"cat '{path}'"
            else:
                raise ValueError("Could not parse Get-Content command")
        else:
            raise ValueError(f"Unsupported PowerShell command for fallback: {powershell_command}")

        logger.debug(f"Executing fallback bash command: {bash_command}")

        result = subprocess.run(
            bash_command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=self.timeout,
            check=True
        )

        return result.stdout.strip()

    def execute(self, command: str) -> str:
        """
        Execute a PowerShell command and return output.
        Falls back to bash commands if PowerShell is not available.

        Args:
            command: PowerShell command to execute

        Returns:
            Command output as string

        Raises:
            subprocess.TimeoutExpired: If command exceeds timeout
            subprocess.CalledProcessError: If command returns non-zero exit code
            RuntimeError: If command execution fails
        """
        if self.use_fallback:
            try:
                return self._execute_fallback(command)
            except Exception as e:
                logger.error(f"Fallback command failed: {e}")
                raise

        try:
            if self.platform.startswith('win'):
                # Windows PowerShell
                ps_command = ['powershell', '-Command', command]
            else:
                # Unix-like systems with PowerShell Core (pwsh)
                ps_command = ['pwsh', '-Command', command]

            logger.debug(f"Executing PowerShell command: {command}")

            result = subprocess.run(
                ps_command,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                check=True
            )

            return result.stdout.strip()

        except FileNotFoundError:
            # Try alternative PowerShell executable
            try:
                ps_command[0] = 'pwsh' if self.platform.startswith('win') else 'powershell'
                result = subprocess.run(
                    ps_command,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    check=True
                )
                return result.stdout.strip()
            except FileNotFoundError:
                logger.warning("PowerShell not found, switching to fallback mode")
                self.use_fallback = True
                return self._execute_fallback(command)

        except subprocess.TimeoutExpired as e:
            logger.error(f"PowerShell command timed out after {self.timeout}s: {command}")
            raise

        except subprocess.CalledProcessError as e:
            logger.error(f"PowerShell command failed: {e.stderr}")
            raise


class FSA1MetaPatternAnalyzer:
    """
    Meta-Pattern Analyzer for execution logs.

    Analyzes execution logs to identify top-performing patterns and generates
    actionable optimization recommendations.
    """

    def __init__(self, logs_dir: str = "./logs", timeout: int = 30):
        """
        Initialize the analyzer.

        Args:
            logs_dir: Directory containing execution logs
            timeout: Timeout for PowerShell commands in seconds
        """
        self.logs_dir = Path(logs_dir)
        self.ps_executor = PowerShellExecutor(timeout=timeout)
        logger.info(f"Initialized FSA-1 Meta-Pattern Analyzer with logs_dir: {logs_dir}")

    def collect_execution_logs(self, pattern_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Collect execution logs from the logs directory using PowerShell.

        Args:
            pattern_id: Optional pattern ID to filter logs. If None, collects all logs.

        Returns:
            List of parsed log entries as dictionaries

        Raises:
            FileNotFoundError: If logs directory doesn't exist
            json.JSONDecodeError: If log file contains invalid JSON
        """
        logger.info(f"Collecting execution logs from: {self.logs_dir}")

        if not self.logs_dir.exists():
            raise FileNotFoundError(f"Logs directory not found: {self.logs_dir}")

        # Use PowerShell Get-ChildItem to find JSON log files
        if pattern_id:
            # Filter by pattern_id in filename
            ps_command = (
                f"Get-ChildItem -Path '{self.logs_dir}' -Filter '*{pattern_id}*.json' "
                f"-Recurse | Select-Object -ExpandProperty FullName"
            )
        else:
            # Get all JSON files
            ps_command = (
                f"Get-ChildItem -Path '{self.logs_dir}' -Filter '*.json' "
                f"-Recurse | Select-Object -ExpandProperty FullName"
            )

        try:
            output = self.ps_executor.execute(ps_command)

            if not output:
                logger.warning("No log files found")
                return []

            log_files = output.split('\n')
            logger.info(f"Found {len(log_files)} log file(s)")

            logs = []
            for log_file in log_files:
                log_file = log_file.strip()
                if not log_file:
                    continue

                try:
                    # Read file content using PowerShell
                    read_command = f"Get-Content -Path '{log_file}' -Raw"
                    content = self.ps_executor.execute(read_command)

                    if content:
                        log_entry = json.loads(content)
                        log_entry['_source_file'] = log_file
                        logs.append(log_entry)
                        logger.debug(f"Successfully parsed: {log_file}")

                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON in {log_file}: {e}")
                    continue
                except Exception as e:
                    logger.error(f"Error reading {log_file}: {e}")
                    continue

            logger.info(f"Successfully collected {len(logs)} log entries")
            return logs

        except Exception as e:
            logger.error(f"Error collecting logs: {e}")
            raise

    def analyze_pattern_performance(self, logs: List[Dict[str, Any]]) -> Dict[str, PatternStatistics]:
        """
        Analyze performance metrics for each pattern.

        Args:
            logs: List of log entries to analyze

        Returns:
            Dictionary mapping pattern_id to PatternStatistics
        """
        logger.info(f"Analyzing performance for {len(logs)} log entries")

        # Group logs by pattern_id
        pattern_groups = defaultdict(list)
        for log in logs:
            pattern_id = log.get('pattern_id', 'unknown')
            pattern_groups[pattern_id].append(log)

        logger.info(f"Found {len(pattern_groups)} unique patterns")

        # Calculate statistics for each pattern
        statistics = {}
        for pattern_id, pattern_logs in pattern_groups.items():
            lq_scores = []
            success_count = 0
            failure_count = 0
            execution_times = []

            for log in pattern_logs:
                # Extract LQ score
                lq_score = log.get('lq_score')
                if lq_score is None:
                    lq_score = log.get('quality_score', 0.0)
                if isinstance(lq_score, (int, float)):
                    lq_scores.append(float(lq_score))

                # Count successes/failures
                success = log.get('success')
                if success is None:
                    success = log.get('status') == 'success'
                if success is None:
                    success = True  # Default to success if not specified
                if success:
                    success_count += 1
                else:
                    failure_count += 1

                # Extract execution time
                exec_time = log.get('execution_time')
                if exec_time is None:
                    exec_time = log.get('duration', 0.0)
                if isinstance(exec_time, (int, float)):
                    execution_times.append(float(exec_time))

            # Calculate statistics
            if lq_scores:
                mean_lq = mean(lq_scores)
                max_lq = max(lq_scores)
                min_lq = min(lq_scores)
                std_lq = stdev(lq_scores) if len(lq_scores) > 1 else 0.0
            else:
                mean_lq = max_lq = min_lq = std_lq = 0.0

            total_executions = success_count + failure_count
            success_rate = (success_count / total_executions * 100) if total_executions > 0 else 0.0
            avg_exec_time = mean(execution_times) if execution_times else 0.0

            stats = PatternStatistics(
                pattern_id=pattern_id,
                execution_count=total_executions,
                mean_lq_score=round(mean_lq, 4),
                max_lq_score=round(max_lq, 4),
                min_lq_score=round(min_lq, 4),
                std_dev_lq_score=round(std_lq, 4),
                success_rate=round(success_rate, 2),
                total_successes=success_count,
                total_failures=failure_count,
                avg_execution_time=round(avg_exec_time, 4)
            )

            statistics[pattern_id] = stats
            logger.debug(f"Pattern {pattern_id}: {total_executions} executions, "
                        f"{success_rate:.2f}% success, LQ: {mean_lq:.4f}")

        return statistics

    def generate_recommendations(
        self,
        analysis: Dict[str, PatternStatistics]
    ) -> List[Recommendation]:
        """
        Generate optimization recommendations based on pattern analysis.

        Args:
            analysis: Dictionary of pattern statistics

        Returns:
            List of recommendations sorted by priority
        """
        logger.info("Generating optimization recommendations")

        if not analysis:
            logger.warning("No analysis data available for recommendations")
            return []

        recommendations = []

        # Sort patterns by mean LQ score
        sorted_patterns = sorted(
            analysis.values(),
            key=lambda x: x.mean_lq_score,
            reverse=True
        )

        # Identify top performers (top 20% or at least top 3)
        top_count = max(3, len(sorted_patterns) // 5)
        top_performers = sorted_patterns[:top_count]

        # Recommendation 1: Promote top-performing patterns
        for i, pattern in enumerate(top_performers, 1):
            if pattern.mean_lq_score > 0.7:  # High quality threshold
                rec = Recommendation(
                    priority="HIGH",
                    pattern_id=pattern.pattern_id,
                    recommendation_type="PROMOTE",
                    description=(
                        f"Pattern '{pattern.pattern_id}' shows excellent performance "
                        f"with mean LQ score of {pattern.mean_lq_score:.4f} and "
                        f"{pattern.success_rate:.2f}% success rate. Consider using "
                        f"this pattern as a template for similar use cases."
                    ),
                    expected_impact="High - Can improve overall system quality by 15-25%",
                    metrics={
                        "rank": i,
                        "mean_lq_score": pattern.mean_lq_score,
                        "success_rate": pattern.success_rate,
                        "execution_count": pattern.execution_count,
                        "consistency": 1.0 - (pattern.std_dev_lq_score / pattern.mean_lq_score)
                        if pattern.mean_lq_score > 0 else 0.0
                    }
                )
                recommendations.append(rec)

        # Recommendation 2: Investigate low performers
        low_performers = [p for p in sorted_patterns if p.mean_lq_score < 0.5]
        for pattern in low_performers:
            rec = Recommendation(
                priority="MEDIUM",
                pattern_id=pattern.pattern_id,
                recommendation_type="INVESTIGATE",
                description=(
                    f"Pattern '{pattern.pattern_id}' shows below-average performance "
                    f"with mean LQ score of {pattern.mean_lq_score:.4f}. "
                    f"Review and refactor this pattern or consider deprecation."
                ),
                expected_impact="Medium - Can prevent quality degradation",
                metrics={
                    "mean_lq_score": pattern.mean_lq_score,
                    "success_rate": pattern.success_rate,
                    "execution_count": pattern.execution_count
                }
            )
            recommendations.append(rec)

        # Recommendation 3: Optimize high-variance patterns
        high_variance = [
            p for p in sorted_patterns
            if p.std_dev_lq_score > 0.2 and p.execution_count > 5
        ]
        for pattern in high_variance:
            rec = Recommendation(
                priority="MEDIUM",
                pattern_id=pattern.pattern_id,
                recommendation_type="STABILIZE",
                description=(
                    f"Pattern '{pattern.pattern_id}' shows high variance "
                    f"(std dev: {pattern.std_dev_lq_score:.4f}). "
                    f"Investigate inconsistency and add guards or validation."
                ),
                expected_impact="Medium - Improves reliability and predictability",
                metrics={
                    "mean_lq_score": pattern.mean_lq_score,
                    "std_dev_lq_score": pattern.std_dev_lq_score,
                    "coefficient_of_variation": pattern.std_dev_lq_score / pattern.mean_lq_score
                    if pattern.mean_lq_score > 0 else 0.0
                }
            )
            recommendations.append(rec)

        # Recommendation 4: Scale successful patterns
        scalable_patterns = [
            p for p in top_performers
            if p.execution_count < 10 and p.success_rate > 90
        ]
        for pattern in scalable_patterns:
            rec = Recommendation(
                priority="LOW",
                pattern_id=pattern.pattern_id,
                recommendation_type="SCALE",
                description=(
                    f"Pattern '{pattern.pattern_id}' shows high success rate "
                    f"({pattern.success_rate:.2f}%) but limited usage "
                    f"({pattern.execution_count} executions). Consider expanding "
                    f"its application to similar scenarios."
                ),
                expected_impact="Low-Medium - Potential for broader application",
                metrics={
                    "mean_lq_score": pattern.mean_lq_score,
                    "success_rate": pattern.success_rate,
                    "execution_count": pattern.execution_count
                }
            )
            recommendations.append(rec)

        # Sort recommendations by priority
        priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        recommendations.sort(key=lambda x: priority_order[x.priority])

        logger.info(f"Generated {len(recommendations)} recommendations")
        return recommendations

    def run_analysis(self, pattern_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Orchestrate the complete analysis pipeline.

        Args:
            pattern_id: Optional pattern ID to filter analysis

        Returns:
            Complete analysis report as dictionary
        """
        logger.info("Starting FSA-1 Meta-Pattern Analysis")
        start_time = datetime.now()

        try:
            # Step 1: Collect logs
            logs = self.collect_execution_logs(pattern_id=pattern_id)

            if not logs:
                logger.warning("No logs found to analyze")
                return {
                    "status": "completed",
                    "timestamp": datetime.now().isoformat(),
                    "analysis_duration_seconds": 0,
                    "logs_analyzed": 0,
                    "patterns_found": 0,
                    "statistics": {},
                    "recommendations": [],
                    "message": "No logs found in the specified directory"
                }

            # Step 2: Analyze performance
            statistics = self.analyze_pattern_performance(logs)

            # Step 3: Generate recommendations
            recommendations = self.generate_recommendations(statistics)

            # Calculate analysis duration
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            # Build report
            report = {
                "status": "completed",
                "timestamp": end_time.isoformat(),
                "analysis_duration_seconds": round(duration, 2),
                "logs_analyzed": len(logs),
                "patterns_found": len(statistics),
                "statistics": {
                    pid: asdict(stats)
                    for pid, stats in statistics.items()
                },
                "recommendations": [
                    asdict(rec) for rec in recommendations
                ],
                "summary": {
                    "top_pattern": max(
                        statistics.values(),
                        key=lambda x: x.mean_lq_score
                    ).pattern_id if statistics else None,
                    "average_success_rate": round(
                        mean([s.success_rate for s in statistics.values()]),
                        2
                    ) if statistics else 0.0,
                    "total_executions": sum(
                        s.execution_count for s in statistics.values()
                    ),
                    "high_priority_recommendations": len(
                        [r for r in recommendations if r.priority == "HIGH"]
                    )
                }
            }

            logger.info("Analysis completed successfully")
            return report

        except Exception as e:
            logger.error(f"Analysis failed: {e}", exc_info=True)
            return {
                "status": "failed",
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "error_type": type(e).__name__
            }


def main():
    """Main execution block."""
    import argparse

    parser = argparse.ArgumentParser(
        description="FSA-1: Meta-Pattern Analyzer - Analyze execution logs and generate optimization recommendations"
    )
    parser.add_argument(
        '--logs-dir',
        type=str,
        default='./logs',
        help='Directory containing execution logs (default: ./logs)'
    )
    parser.add_argument(
        '--pattern-id',
        type=str,
        default=None,
        help='Filter analysis by specific pattern ID'
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=30,
        help='Timeout for PowerShell commands in seconds (default: 30)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='Output file path for JSON report (default: stdout)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Run analysis
    analyzer = FSA1MetaPatternAnalyzer(
        logs_dir=args.logs_dir,
        timeout=args.timeout
    )

    report = analyzer.run_analysis(pattern_id=args.pattern_id)

    # Output report
    report_json = json.dumps(report, indent=2)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report_json)
        logger.info(f"Report written to: {args.output}")
    else:
        print(report_json)

    # Exit with appropriate code
    sys.exit(0 if report.get('status') == 'completed' else 1)


if __name__ == '__main__':
    main()
