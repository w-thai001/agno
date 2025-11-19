#!/bin/bash

# Git History Analysis for FSA Projects
# Date Range: 2025-11-18 00:00:00 to 2025-11-19 08:00:00
# NO file_list - ONLY git commands

echo "=================================================="
echo "FSA PROJECT GIT HISTORY ANALYSIS"
echo "=================================================="
echo ""
echo "Date Range: 2025-11-18 00:00:00 to 2025-11-19 08:00:00 PST"
echo "Timestamp: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# Convert PST to UTC for git log (PST is UTC-8)
START_DATE="2025-11-18 08:00:00"  # 2025-11-18 00:00:00 PST = 08:00:00 UTC
END_DATE="2025-11-19 16:00:00"    # 2025-11-19 08:00:00 PST = 16:00:00 UTC

echo "=================================================="
echo "1. SEARCHING ALL BRANCHES FOR FSA-RELATED COMMITS"
echo "=================================================="
echo ""

# Fetch all remote branches to ensure we have complete history
git fetch --all 2>/dev/null

echo "--- All branches in repository ---"
git branch -a
echo ""

echo "=================================================="
echo "2. COMMITS WITH 'FSA' IN MESSAGE (DATE FILTERED)"
echo "=================================================="
echo ""
git log --all --since="$START_DATE" --until="$END_DATE" --grep="FSA" --grep="fsa" -i --oneline --decorate
FSA_COMMIT_COUNT=$(git log --all --since="$START_DATE" --until="$END_DATE" --grep="FSA" --grep="fsa" -i --oneline | wc -l)
echo ""
echo "Total FSA commits in date range: $FSA_COMMIT_COUNT"
echo ""

echo "=================================================="
echo "3. COMMITS WITH 'MARATHON' IN MESSAGE"
echo "=================================================="
echo ""
git log --all --since="$START_DATE" --until="$END_DATE" --grep="marathon" -i --oneline --decorate
MARATHON_COMMIT_COUNT=$(git log --all --since="$START_DATE" --until="$END_DATE" --grep="marathon" -i --oneline | wc -l)
echo ""
echo "Total marathon commits in date range: $MARATHON_COMMIT_COUNT"
echo ""

echo "=================================================="
echo "4. ALL COMMITS IN DATE RANGE (FULL DETAILS)"
echo "=================================================="
echo ""
git log --all --since="$START_DATE" --until="$END_DATE" --format="%H|%ai|%an|%s" --name-status
echo ""

ALL_COMMITS_COUNT=$(git log --all --since="$START_DATE" --until="$END_DATE" --oneline | wc -l)
echo "Total commits in date range: $ALL_COMMITS_COUNT"
echo ""

echo "=================================================="
echo "5. SEARCHING FOR FSA-RELATED FILE CHANGES"
echo "=================================================="
echo ""

echo "--- Files with 'fsa' in path (added/modified in date range) ---"
git log --all --since="$START_DATE" --until="$END_DATE" --name-only --diff-filter=AM --format="" | grep -i "fsa" | sort -u
FSA_FILES=$(git log --all --since="$START_DATE" --until="$END_DATE" --name-only --diff-filter=AM --format="" | grep -i "fsa" | wc -l)
echo ""
echo "Total FSA-related files changed: $FSA_FILES"
echo ""

echo "--- Files with 'marathon' in path ---"
git log --all --since="$START_DATE" --until="$END_DATE" --name-only --diff-filter=AM --format="" | grep -i "marathon" | sort -u
MARATHON_FILES=$(git log --all --since="$START_DATE" --until="$END_DATE" --name-only --diff-filter=AM --format="" | grep -i "marathon" | wc -l)
echo ""
echo "Total marathon-related files changed: $MARATHON_FILES"
echo ""

echo "--- Files with 'state' in path ---"
git log --all --since="$START_DATE" --until="$END_DATE" --name-only --diff-filter=AM --format="" | grep -i "state" | sort -u
echo ""

echo "=================================================="
echo "6. DETAILED FSA COMMIT ANALYSIS"
echo "=================================================="
echo ""

if [ $FSA_COMMIT_COUNT -gt 0 ]; then
    echo "--- Full details of FSA commits ---"
    git log --all --since="$START_DATE" --until="$END_DATE" --grep="FSA" --grep="fsa" -i --format="%n%H%n%ai%n%an <%ae>%n%s%n%b%n---FILES---" --name-status
    echo ""
fi

echo "=================================================="
echo "7. RECENT BRANCHES (POSSIBLY FSA-RELATED)"
echo "=================================================="
echo ""

echo "--- Branches updated in date range ---"
git for-each-ref --sort=-committerdate refs/heads/ refs/remotes/ --format='%(refname:short)|%(committerdate:iso8601)|%(committername)' | head -20
echo ""

echo "=================================================="
echo "8. SEARCHING COMMIT CONTENT FOR FSA PATTERNS"
echo "=================================================="
echo ""

echo "--- Commits that modified files containing 'FSA' in content ---"
git log --all --since="$START_DATE" --until="$END_DATE" -S"FSA" --oneline --name-status
echo ""

echo "--- Commits that modified files containing 'marathon' in content ---"
git log --all --since="$START_DATE" --until="$END_DATE" -S"marathon" --oneline --name-status
echo ""

echo "=================================================="
echo "9. SUMMARY STATISTICS"
echo "=================================================="
echo ""
echo "Date Range: 2025-11-18 00:00:00 to 2025-11-19 08:00:00 PST"
echo "Analysis Timestamp: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""
echo "Total commits in date range: $ALL_COMMITS_COUNT"
echo "FSA-related commits: $FSA_COMMIT_COUNT"
echo "Marathon-related commits: $MARATHON_COMMIT_COUNT"
echo "FSA-related file changes: $FSA_FILES"
echo "Marathon-related file changes: $MARATHON_FILES"
echo ""

if [ $FSA_COMMIT_COUNT -gt 0 ] || [ $MARATHON_COMMIT_COUNT -gt 0 ]; then
    echo "FSA WORK DETECTED IN GIT HISTORY!"
else
    echo "NO FSA-RELATED WORK FOUND IN GIT HISTORY FOR THIS DATE RANGE"
fi
echo ""
echo "=================================================="
