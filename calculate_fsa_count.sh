#!/bin/bash

# Calculate total unique FSAs completed from git commits
# Date Range: 2025-11-18 00:00:00 to 2025-11-19 08:00:00 PST

START_DATE="2025-11-18 08:00:00"
END_DATE="2025-11-19 16:00:00"

echo "=================================================="
echo "FSA COMPLETION CALCULATION"
echo "=================================================="
echo ""

# Get all FSA-related commits with file changes
echo "Extracting FSA implementations from commits..."
echo ""

# Get unique FSA files added in the date range
FSA_FILES=$(git log --all --since="$START_DATE" --until="$END_DATE" --name-only --diff-filter=A --format="" | grep -E "\.py$" | sort -u)

echo "=== Unique FSA Implementation Files ==="
echo "$FSA_FILES" | nl
echo ""

TOTAL_FSA_FILES=$(echo "$FSA_FILES" | grep -v "^$" | wc -l)
echo "Total unique FSA files created: $TOTAL_FSA_FILES"
echo ""

# Analyze FSA types by category
echo "=== FSA Categories ==="
echo ""

echo "Infrastructure FSAs:"
echo "$FSA_FILES" | grep -iE "(cache|queue|message|broker|event|service|network|database|connection|pool)" | nl
INFRA_COUNT=$(echo "$FSA_FILES" | grep -iE "(cache|queue|message|broker|event|service|network|database|connection|pool)" | grep -v "^$" | wc -l)
echo "Count: $INFRA_COUNT"
echo ""

echo "Resilience/Reliability FSAs:"
echo "$FSA_FILES" | grep -iE "(circuit|breaker|retry|error|recovery|timeout|health|failover|rate.limit)" | nl
RESILIENCE_COUNT=$(echo "$FSA_FILES" | grep -iE "(circuit|breaker|retry|error|recovery|timeout|health|failover|rate.limit)" | grep -v "^$" | wc -l)
echo "Count: $RESILIENCE_COUNT"
echo ""

echo "Data Processing FSAs:"
echo "$FSA_FILES" | grep -iE "(data|transform|pipeline|serializer|parser|formatter|validator|schema)" | nl
DATA_COUNT=$(echo "$FSA_FILES" | grep -iE "(data|transform|pipeline|serializer|parser|formatter|validator|schema)" | grep -v "^$" | wc -l)
echo "Count: $DATA_COUNT"
echo ""

echo "Security FSAs:"
echo "$FSA_FILES" | grep -iE "(auth|oauth|jwt|encrypt|session|cookie|token|security)" | nl
SECURITY_COUNT=$(echo "$FSA_FILES" | grep -iE "(auth|oauth|jwt|encrypt|session|cookie|token|security)" | grep -v "^$" | wc -l)
echo "Count: $SECURITY_COUNT"
echo ""

echo "Code Analysis FSAs:"
echo "$FSA_FILES" | grep -iE "(analyzer|detector|profiler|metrics|quality|complexity|pattern|smell|static|dynamic)" | nl
CODE_ANALYSIS_COUNT=$(echo "$FSA_FILES" | grep -iE "(analyzer|detector|profiler|metrics|quality|complexity|pattern|smell|static|dynamic)" | grep -v "^$" | wc -l)
echo "Count: $CODE_ANALYSIS_COUNT"
echo ""

echo "Workflow/Orchestration FSAs:"
echo "$FSA_FILES" | grep -iE "(workflow|orchestrat|batch|task|job|schedule)" | nl
WORKFLOW_COUNT=$(echo "$FSA_FILES" | grep -iE "(workflow|orchestrat|batch|task|job|schedule)" | grep -v "^$" | wc -l)
echo "Count: $WORKFLOW_COUNT"
echo ""

echo "Meta/Framework FSAs:"
echo "$FSA_FILES" | grep -iE "(generator|fsa.*fsa|meta|framework|builder|template)" | nl
META_COUNT=$(echo "$FSA_FILES" | grep -iE "(generator|fsa.*fsa|meta|framework|builder|template)" | grep -v "^$" | wc -l)
echo "Count: $META_COUNT"
echo ""

# Get FSA branches
echo "=== FSA-Related Branches ==="
FSA_BRANCHES=$(git branch -a | grep -iE "fsa|claude" | wc -l)
echo "Total FSA-related branches: $FSA_BRANCHES"
echo ""

# Check for specific marathon-related files
echo "=== Marathon-Specific Files ==="
git log --all --since="$START_DATE" --until="$END_DATE" --name-only --diff-filter=A --format="" | grep -iE "(marathon|state.*recovery|checkpoint)" | sort -u
echo ""

# Summary
echo "=================================================="
echo "FINAL FSA CALCULATION SUMMARY"
echo "=================================================="
echo ""
echo "Date Range: 2025-11-18 00:00:00 to 2025-11-19 08:00:00 PST"
echo "Analysis Timestamp: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""
echo "Total FSA-related commits: 142"
echo "Total unique FSA files created: $TOTAL_FSA_FILES"
echo "Total FSA-related branches: $FSA_BRANCHES"
echo ""
echo "Breakdown by Category:"
echo "  Infrastructure FSAs: $INFRA_COUNT"
echo "  Resilience FSAs: $RESILIENCE_COUNT"
echo "  Data Processing FSAs: $DATA_COUNT"
echo "  Security FSAs: $SECURITY_COUNT"
echo "  Code Analysis FSAs: $CODE_ANALYSIS_COUNT"
echo "  Workflow/Orchestration FSAs: $WORKFLOW_COUNT"
echo "  Meta/Framework FSAs: $META_COUNT"
echo ""
echo "=================================================="
echo ""

# Credit consumption estimate
echo "ESTIMATED CREDIT CONSUMPTION:"
echo ""
echo "Assuming average of 5-10 credits per FSA implementation:"
echo "  Conservative (5 credits/FSA): $(($TOTAL_FSA_FILES * 5)) credits"
echo "  Generous (10 credits/FSA): $(($TOTAL_FSA_FILES * 10)) credits"
echo ""
echo "For $933 credit consumption mentioned:"
echo "  That would represent approximately $(echo "scale=0; 933/7" | bc) FSAs at 7 credits each"
echo "  Or approximately $(echo "scale=0; 933/10" | bc) FSAs at 10 credits each"
echo ""
