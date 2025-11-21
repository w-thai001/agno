# FSA-7: Ontology Builder & Semantic Mapper

**Platform:** Claude Code ONLY
**Constraint:** PowerShell subprocess ONLY (NO file_list, NO read_list)
**Tier:** 3 (Intelligence)
**Learning Quotient (LQ):** 2.60
**RE Potential:** ⭐⭐⭐⭐
**Duration:** ~3.2 hrs

## Overview

FSA-7 provides comprehensive ontology management for the FSA ecosystem, enabling:
- FSA taxonomy building
- Relationship mapping (depends_on, enhances, prerequisite_for, conflicts_with)
- Semantic validation
- Knowledge graph visualization (JSON/GraphML format)
- Curriculum prerequisites tracking

## Architecture

### Core Components

1. **TaxonomyBuilder**: Constructs and maintains FSA hierarchies
2. **RelationshipMapper**: Maps complex relationships between FSAs
3. **SemanticValidator**: Validates workflows and detects conflicts
4. **KnowledgeGraphExporter**: Exports ontology to JSON and GraphML formats

### FSA Ontology Schema

Each FSA entity contains:
- `id`: Unique identifier (e.g., "FSA-1")
- `name`: Human-readable name
- `tier`: Complexity tier (1-4)
- `duration`: Estimated implementation time
- `lq`: Learning Quotient (difficulty measure)
- `re_potential`: Recursive Enhancement potential (1-5 stars)
- `components`: List of internal components
- `tools`: Required tools and technologies
- `constraints`: Implementation constraints
- `capabilities`: Inputs, outputs, and side effects

### Relationship Types

- **DEPENDS_ON**: Hard dependency (execution order required)
- **ENHANCES**: Enhancement relationship (improves another FSA)
- **PREREQUISITE_FOR**: Learning prerequisite (recommended order)
- **CONFLICTS_WITH**: Conflict relationship (incompatible)
- **INTEGRATES_WITH**: Integration relationship (work together)
- **EXTENDS**: Extension relationship (builds upon)

## Initial Ontology

FSA-7 includes pre-loaded data for 10 FSAs:

### Tier 1: Foundation
- **FSA-1**: Meta-Pattern Analyzer (LQ 2.93, RE ⭐⭐⭐⭐⭐)
- **FSA-2**: Autonomous Workflow Composer (LQ 2.40, RE ⭐⭐⭐⭐⭐)
- **FSA-3**: RSI Data Aggregator (LQ 2.70, RE ⭐⭐⭐⭐⭐)

### Tier 2: Coordination
- **FSA-4**: Parallel Session Manager (LQ 3.20, RE ⭐⭐⭐⭐)
- **FSA-5**: Cross-Agent Communication Protocol (LQ 2.80, RE ⭐⭐⭐⭐)
- **FSA-6**: Checkpoint & State Persistence (LQ 3.50, RE ⭐⭐⭐⭐)

### Tier 3: Intelligence
- **FSA-7**: Ontology Builder (LQ 2.60, RE ⭐⭐⭐⭐)
- **FSA-8**: Curriculum Learning Sequencer (LQ 3.04, RE ⭐⭐⭐⭐⭐)

### Tier 4: Quality Assurance
- **FSA-9**: PowerShell Compliance Validator (LQ 4.00, RE ⭐⭐⭐)
- **FSA-10**: Test Suite Generator (LQ 3.30, RE ⭐⭐⭐⭐)

## Usage

### Basic Usage

```python
from fsa7_ontology_builder import OntologyBuilder

# Initialize ontology with 10 pre-loaded FSAs
ontology = OntologyBuilder()

print(f"Loaded {len(ontology.entities)} FSAs")
print(f"Loaded {len(ontology.relationships)} relationships")
```

### Semantic Query Methods

#### 1. Find Dependencies

```python
# Find all FSAs that FSA-2 depends on
deps = ontology.find_dependencies("FSA-2")
for dep in deps:
    print(f"{dep.id}: {dep.name}")
# Output:
# FSA-7: Ontology Builder & Semantic Mapper
# FSA-5: Cross-Agent Communication Protocol
```

#### 2. Get Prerequisites

```python
# Get prerequisites for FSA-8
prereqs = ontology.get_prerequisites("FSA-8")
for prereq in prereqs:
    print(f"{prereq.id}: {prereq.name} (Tier {prereq.tier.value})")
# Output:
# FSA-7: Ontology Builder & Semantic Mapper (Tier 3)
# FSA-1: Meta-Pattern Analyzer (Tier 1)
# FSA-4: Parallel Session Manager (Tier 2)
```

#### 3. Find Enhancement Opportunities

```python
# Find FSAs that enhance other FSAs
enhancements = ontology.find_enhancement_opportunities()
for enhancer, enhanced in enhancements:
    print(f"{enhancer.id} enhances {enhanced.id}")
# Output:
# FSA-1 enhances FSA-3
# FSA-7 enhances FSA-1
```

#### 4. Validate Workflow

```python
# Validate a workflow sequence
workflow = ["FSA-1", "FSA-7", "FSA-8"]
result = ontology.validate_workflow(workflow)

print(f"Valid: {result.is_valid}")
print(f"Errors: {result.errors}")
print(f"Warnings: {result.warnings}")
print(f"Suggestions: {result.suggestions}")
```

#### 5. Calculate Curriculum Path

```python
# Calculate optimal learning path from FSA-1 to FSA-8
path = ontology.calculate_curriculum_path("FSA-1", "FSA-8")

print("Recommended sequence:")
for i, fsa in enumerate(path, 1):
    print(f"{i}. {fsa.id}: {fsa.name} (Tier {fsa.tier.value}, LQ {fsa.lq})")
```

#### 6. Detect Conflicts

```python
# Detect conflicts in a list of FSAs
test_list = ["FSA-6", "FSA-9", "FSA-10"]
conflicts = ontology.detect_conflicts(test_list)

for conflict in conflicts:
    print(f"{conflict.conflict_type}: {conflict.description}")
    print(f"Severity: {conflict.severity}")
    if conflict.resolution:
        print(f"Resolution: {conflict.resolution}")
```

### Knowledge Graph Export

#### JSON Export

```python
# Export to JSON format
json_data = ontology.export_to_json(include_metadata=True)

# Save to file via PowerShell
ontology.save_to_file_powershell("fsa_ontology.json", format='json')
```

JSON structure:
```json
{
  "ontology_version": "1.0",
  "generated_at": "2025-11-21T...",
  "operation_lq": 3.5,
  "nodes": [...],
  "edges": [...],
  "statistics": {
    "total_fsas": 10,
    "total_relationships": 19,
    "tier_distribution": {...},
    "avg_lq": 3.05,
    "avg_re_potential": 4.30
  }
}
```

#### GraphML Export

```python
# Export to GraphML format (for Gephi, yEd, Cytoscape)
graphml_str = ontology.export_to_graphml()

# Save to file via PowerShell
ontology.save_to_file_powershell("fsa_ontology.graphml", format='graphml')
```

GraphML can be visualized in:
- **Gephi**: Network visualization tool
- **yEd**: Graph editor
- **Cytoscape**: Network analysis tool
- **Neo4j**: Graph database

### Loading from Files

```python
# Load ontology from JSON file
ontology = OntologyBuilder()
ontology.load_from_file_powershell("fsa_ontology.json", format='json')

# Load ontology from GraphML file
ontology = OntologyBuilder()
ontology.load_from_file_powershell("fsa_ontology.graphml", format='graphml')
```

### Cypher-like Queries

```python
# Query all Tier 1 FSAs
results = ontology.query_cypher_like("MATCH (a) WHERE a.tier = 1 RETURN a")

# Query FSAs with LQ > 3.0
results = ontology.query_cypher_like("MATCH (a) WHERE a.lq > 3.0 RETURN a")

# Query all dependency relationships
results = ontology.query_cypher_like("MATCH (a)-[r:DEPENDS_ON]->(b) RETURN a, r, b")
```

### Summary Report

```python
# Generate human-readable summary
report = ontology.generate_summary_report()
print(report)
```

## MLA v3.0 Integration

FSA-7 uses MLA v3.0 for Learning Quotient calculations:

```python
# Calculate LQ for operations
lq_simple = ontology.mla_calculator.calculate_operation_lq(
    'query_simple',
    entities_count=10,
    relationships_count=19
)

lq_complex = ontology.mla_calculator.calculate_operation_lq(
    'query_complex',
    entities_count=10,
    relationships_count=19,
    complexity_factor=1.2
)

# Calculate recursive enhancement
new_re = ontology.mla_calculator.calculate_recursive_enhancement(
    current_re=4,
    successful_iterations=5,
    knowledge_gain=2.5
)
```

Operation types and base LQ values:
- `query_simple`: 1.5
- `query_complex`: 2.5
- `graph_export`: 2.0
- `validation`: 3.0
- `path_finding`: 3.5
- `conflict_detection`: 2.8

## PowerShell Compliance

FSA-7 uses PowerShell subprocess for all file operations:

### Windows (powershell.exe)
```powershell
# Save file
Set-Content -Path 'file.json' -Value @'
{content}
'@ -Encoding UTF8

# Load file
Get-Content -Path 'file.json' -Raw
```

### PowerShell Core (pwsh)
```powershell
# Cross-platform PowerShell Core
pwsh -NoProfile -Command "Set-Content -Path 'file.json' ..."
```

### Fallback Mode
On non-Windows systems without PowerShell, FSA-7 automatically falls back to direct file I/O while maintaining the same interface.

## Integration with Other FSAs

### FSA-2: Autonomous Workflow Composer
```python
# FSA-2 uses ontology for workflow composition
ontology = OntologyBuilder()
workflow = ["FSA-1", "FSA-2", "FSA-3"]

# Validate workflow before execution
validation = ontology.validate_workflow(workflow)
if validation.is_valid:
    # Execute workflow
    pass
```

### FSA-8: Curriculum Learning Sequencer
```python
# FSA-8 uses ontology for curriculum sequencing
ontology = OntologyBuilder()

# Calculate optimal learning path
path = ontology.calculate_curriculum_path("FSA-1", "FSA-10")

# Sequence FSAs by difficulty
for fsa in path:
    print(f"Learn: {fsa.name} (LQ: {fsa.lq})")
```

### FSA-1: Meta-Pattern Analyzer
```python
# FSA-1 uses ontology for pattern analysis
ontology = OntologyBuilder()

# Analyze FSA patterns
tier_1_fsas = [e for e in ontology.entities.values() if e.tier.value == 1]
patterns = analyze_patterns(tier_1_fsas)
```

## Advanced Usage

### Custom Entities

```python
from fsa7_ontology_builder import FSAEntity, FSATier, FSACapability

# Create custom FSA
custom_fsa = FSAEntity(
    id="FSA-11",
    name="Custom Agent",
    tier=FSATier.TIER_2,
    duration="~4 hrs",
    lq=2.8,
    re_potential=4,
    components=["Component1", "Component2"],
    tools=["PowerShell", "Python"],
    constraints=["PowerShell subprocess only"],
    capabilities=FSACapability(
        inputs=["input1", "input2"],
        outputs=["output1"],
        side_effects=["creates cache"]
    ),
    description="Custom FSA for specific task"
)

# Add to ontology
ontology.add_entity(custom_fsa)
```

### Custom Relationships

```python
from fsa7_ontology_builder import RelationshipType

# Add custom relationship
ontology.add_relationship(
    source_id="FSA-11",
    target_id="FSA-1",
    rel_type=RelationshipType.DEPENDS_ON,
    strength=0.8,
    metadata={"reason": "Custom dependency"}
)
```

## Testing

Run the demo:
```bash
python fsa7_ontology_builder.py
```

Run PowerShell file operations tests:
```bash
python test_fsa7_powershell.py
```

## Performance

- **Entity Queries**: O(1) lookup by ID
- **Relationship Queries**: O(R) where R = number of relationships
- **Path Finding**: O(N + R) BFS traversal
- **Validation**: O(N * R) worst case
- **Export**: O(N + R) serialization

## Limitations

1. **PowerShell Requirement**: Requires PowerShell on Windows (fallback available)
2. **In-Memory Storage**: Ontology stored in memory (no database)
3. **Simple Query Language**: Basic Cypher-like queries only
4. **No Versioning**: Single version of ontology at a time

## Future Enhancements

- [ ] Graph database backend (Neo4j integration)
- [ ] Advanced Cypher query support
- [ ] Ontology versioning and migration
- [ ] Visualization web interface
- [ ] Automated relationship inference
- [ ] Collaborative ontology editing
- [ ] Integration with external knowledge bases

## License

Part of the Agno FSA ecosystem.

## See Also

- FSA-1: Meta-Pattern Analyzer
- FSA-2: Autonomous Workflow Composer
- FSA-8: Curriculum Learning Sequencer
- MLA v3.0 Documentation
