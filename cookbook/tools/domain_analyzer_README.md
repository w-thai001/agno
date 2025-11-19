# Domain Analyzer FSA

A comprehensive Domain Analyzer Finite State Automaton (FSA) for the Agno Framework that provides intelligent domain modeling and reasoning capabilities.

## Overview

The Domain Analyzer FSA helps you analyze and understand domain-specific contexts, extract entities and relationships, discover business rules, and generate comprehensive domain models automatically.

## Key Capabilities

- **Domain Entity Extraction**: Automatically extract entities from natural language descriptions
- **Entity Classification**: Classify entities as aggregates, entities, value objects, or services
- **Relationship Mapping**: Discover and map relationships between domain entities
- **Dependency Analysis**: Analyze dependencies and identify circular references or coupling issues
- **Business Rule Discovery**: Extract business rules and constraints from domain descriptions
- **Domain Ontology Building**: Build hierarchical domain ontologies
- **Vocabulary Extraction**: Create domain-specific glossaries and terminology
- **Reasoning & Inference**: Perform context-aware reasoning and infer implicit relationships
- **Model Generation**: Generate domain models in JSON, UML, or diagram formats
- **Model Validation**: Validate domain models for consistency and completeness
- **Model Evolution**: Evolve domain models as new information becomes available

## Installation

The Domain Analyzer is included in the Agno tools package:

```python
from agno.tools.domain_analyzer import DomainAnalyzer
```

## Quick Start

### Basic Usage with Agent

```python
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.domain_analyzer import DomainAnalyzer

# Create Domain Analyzer
analyzer = DomainAnalyzer()

# Create agent with Domain Analyzer
agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    tools=[analyzer],
    show_tool_calls=True,
)

# Analyze a domain
agent.print_response("""
Analyze this e-commerce domain:
A Customer can place Orders. Each Order contains OrderItems.
An OrderItem references a Product. Orders must have payment information.
""")
```

### Direct Tool Usage

```python
from agno.tools.domain_analyzer import DomainAnalyzer

# Create analyzer
analyzer = DomainAnalyzer()

# Extract entities
result = analyzer.extract_entities(
    domain_description="A Customer can place Orders...",
    sample_data='{"customer": {"id": 1, "email": "test@example.com"}}'
)

# Map relationships
relationships = analyzer.map_relationships(
    domain_description="A Customer can place Orders..."
)

# Generate domain model
model = analyzer.generate_domain_model(format="json")
```

## Configuration Options

You can enable/disable specific capabilities when creating the analyzer:

```python
analyzer = DomainAnalyzer(
    name="my_analyzer",
    enable_entity_extraction=True,      # Extract entities from descriptions
    enable_relationship_mapping=True,   # Map entity relationships
    enable_business_rules=True,         # Discover business rules
    enable_ontology_building=True,      # Build domain ontologies
    enable_reasoning=True,              # Enable reasoning capabilities
    enable_model_generation=True,       # Generate domain models
    enable_validation=True,             # Validate models
)
```

## Core Methods

### Entity Extraction & Classification

#### `extract_entities(domain_description: str, sample_data: Optional[str] = None) -> str`

Extract entities from domain descriptions and sample data.

```python
result = analyzer.extract_entities(
    domain_description="A Customer has an Account. An Account contains Transactions.",
    sample_data='{"customer": {"id": 1, "name": "John"}}'
)
```

#### `classify_entities(entity_name: Optional[str] = None) -> str`

Classify entities into categories (aggregate_root, entity, value_object, service).

```python
classifications = analyzer.classify_entities()  # Classify all entities
specific = analyzer.classify_entities("Customer")  # Classify specific entity
```

### Relationship Mapping

#### `map_relationships(domain_description: str) -> str`

Map relationships between entities.

```python
relationships = analyzer.map_relationships(
    "Customer has many Orders. Order belongs to Customer."
)
```

#### `analyze_dependencies() -> str`

Analyze dependencies between entities and identify issues.

```python
analysis = analyzer.analyze_dependencies()
# Returns: circular dependencies, coupling scores, isolated entities
```

#### `infer_relationships() -> str`

Infer additional relationships based on naming conventions and patterns.

```python
inferred = analyzer.infer_relationships()
# Automatically detects foreign key patterns like customer_id
```

### Business Rules

#### `discover_business_rules(domain_description: str, existing_rules: Optional[str] = None) -> str`

Discover business rules and constraints from descriptions.

```python
rules = analyzer.discover_business_rules(
    "Customer must have valid email. Orders cannot be placed without payment."
)
```

#### `validate_business_rules(sample_data: str) -> str`

Validate business rules against sample data.

```python
validation = analyzer.validate_business_rules(
    '{"customer": {"email": "test@example.com"}}'
)
```

### Ontology & Vocabulary

#### `build_domain_ontology(domain_description: str) -> str`

Build a hierarchical domain ontology.

```python
ontology = analyzer.build_domain_ontology(
    "PremiumCustomer is a type of Customer. GoldCustomer extends PremiumCustomer."
)
```

#### `extract_vocabulary(domain_description: str) -> str`

Extract domain-specific vocabulary and terminology.

```python
vocabulary = analyzer.extract_vocabulary(
    "Customer refers to a registered user. Order means a purchase request."
)
```

### Reasoning

#### `reason_about_domain(query: str) -> str`

Perform context-aware reasoning about the domain.

```python
reasoning = analyzer.reason_about_domain(
    "What happens when a Customer places an Order?"
)
```

### Model Generation

#### `generate_domain_model(format: str = "json") -> str`

Generate complete domain model in specified format.

Supported formats:
- `"json"`: Complete JSON representation
- `"uml"`: PlantUML class diagram
- `"diagram"`: Text-based diagram

```python
json_model = analyzer.generate_domain_model("json")
uml_model = analyzer.generate_domain_model("uml")
text_diagram = analyzer.generate_domain_model("diagram")
```

#### `evolve_domain_model(new_information: str) -> str`

Evolve the domain model with new information.

```python
evolution = analyzer.evolve_domain_model(
    "Customer can now have Wishlists. Wishlist contains Products."
)
```

### Validation & Recommendations

#### `validate_model(sample_data: Optional[str] = None) -> str`

Validate domain model for consistency and completeness.

```python
validation = analyzer.validate_model(
    '{"customer": {"id": 1, "email": "test@example.com"}}'
)
```

#### `get_recommendations() -> str`

Get recommendations for improving the domain model.

```python
recommendations = analyzer.get_recommendations()
# Returns prioritized suggestions for model improvement
```

### Utility Methods

#### `get_domain_model() -> str`

Get the current domain model with summary statistics.

```python
model = analyzer.get_domain_model()
```

#### `reset_domain_model() -> str`

Reset the domain model to empty state.

```python
analyzer.reset_domain_model()
```

## Output Format

All methods return JSON strings with consistent structure:

```json
{
  "data": { ... },
  "status": "success",
  "metadata": { ... }
}
```

Error responses:

```json
{
  "error": "Error description",
  "status": "failed"
}
```

## Complete Example Workflow

```python
from agno.tools.domain_analyzer import DomainAnalyzer

# Create analyzer
analyzer = DomainAnalyzer()

# 1. Extract entities
domain_desc = """
An e-commerce platform where Customer can place Orders.
Each Order contains OrderItems. OrderItem references a Product.
Customer must have valid email. Orders cannot be placed without payment.
"""

sample_data = """
{
  "customer": {"id": 1, "email": "customer@example.com", "name": "John"},
  "order": {"id": 1001, "customer_id": 1, "status": "pending"},
  "product": {"id": 501, "name": "Widget", "price": 49.99}
}
"""

entities = analyzer.extract_entities(domain_desc, sample_data)

# 2. Classify entities
classifications = analyzer.classify_entities()

# 3. Map relationships
relationships = analyzer.map_relationships(domain_desc)

# 4. Infer additional relationships
inferred = analyzer.infer_relationships()

# 5. Discover business rules
rules = analyzer.discover_business_rules(domain_desc)

# 6. Build ontology
ontology = analyzer.build_domain_ontology(domain_desc)

# 7. Extract vocabulary
vocabulary = analyzer.extract_vocabulary(domain_desc)

# 8. Validate model
validation = analyzer.validate_model(sample_data)

# 9. Get recommendations
recommendations = analyzer.get_recommendations()

# 10. Generate final model
json_model = analyzer.generate_domain_model("json")
uml_model = analyzer.generate_domain_model("uml")

# 11. Evolve model with new info
evolution = analyzer.evolve_domain_model(
    "Customer can have Wishlists containing Products."
)
```

## Use Cases

### 1. Domain-Driven Design (DDD)

Use the Domain Analyzer to quickly prototype domain models following DDD principles:

```python
analyzer.extract_entities(ddd_description)
analyzer.classify_entities()  # Identifies aggregates, entities, value objects
analyzer.map_relationships(ddd_description)
```

### 2. Requirements Analysis

Extract domain knowledge from requirements documents:

```python
analyzer.extract_entities(requirements_doc)
analyzer.discover_business_rules(requirements_doc)
analyzer.build_domain_ontology(requirements_doc)
```

### 3. Legacy System Analysis

Analyze legacy systems by providing sample data:

```python
analyzer.extract_entities("Legacy system", json_dumps(legacy_data))
analyzer.infer_relationships()
analyzer.analyze_dependencies()
```

### 4. API Design

Design APIs based on domain models:

```python
analyzer.extract_entities(api_spec)
analyzer.map_relationships(api_spec)
model = analyzer.generate_domain_model("json")
```

### 5. Database Schema Design

Generate database schemas from domain models:

```python
analyzer.extract_entities(domain_desc, sample_data)
analyzer.infer_relationships()
uml = analyzer.generate_domain_model("uml")
```

## Best Practices

1. **Start with Clear Descriptions**: Provide detailed domain descriptions using natural language
2. **Include Sample Data**: Sample data significantly improves entity extraction accuracy
3. **Iterative Refinement**: Use `evolve_domain_model()` to incrementally improve the model
4. **Validate Regularly**: Run `validate_model()` to catch issues early
5. **Use Recommendations**: Follow suggestions from `get_recommendations()`
6. **Entity Naming**: Use PascalCase for entity names for better pattern recognition
7. **Relationship Keywords**: Use clear relationship keywords (has, contains, belongs to, etc.)
8. **Business Rules**: Express rules clearly using must, should, cannot, always, never

## Pattern Recognition

The analyzer recognizes these patterns:

### Entity Patterns
- "Customer has an Account"
- "entity Order"
- "Order object"

### Relationship Patterns
- "Customer has many Orders" → one_to_many
- "Order has a Customer" → one_to_one
- "OrderItem belongs to Order" → many_to_one
- "Order contains OrderItems" → composition
- "Payment uses PaymentGateway" → dependency
- "PremiumCustomer extends Customer" → inheritance

### Business Rule Patterns
- "must be/have/contain" → constraint
- "should be/have/contain" → recommendation
- "cannot be/have/contain" → prohibition
- "if X then Y" → conditional
- "always X" → invariant
- "never X" → prohibition

### Ontology Patterns
- "X is a type of Y"
- "X extends Y"
- "X inherits from Y"

## Troubleshooting

### No Entities Extracted

- Ensure domain description uses capitalized entity names
- Provide sample data in JSON format
- Use clear entity keywords (entity, object, class, model)

### Missing Relationships

- Use explicit relationship keywords (has, contains, belongs to)
- Provide more detailed domain description
- Use `infer_relationships()` to auto-detect FK patterns

### Validation Errors

- Check for circular dependencies with `analyze_dependencies()`
- Ensure all entities have attributes
- Verify sample data matches entity structure

## Advanced Features

### Custom Validation Logic

The analyzer can be extended with custom validation:

```python
# Current validation results are stored in
validation = analyzer.validate_model(sample_data)
# Extend with custom logic based on your domain
```

### Integration with Agents

Use with Agno agents for conversational domain modeling:

```python
agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    tools=[DomainAnalyzer()],
    instructions="""You are a domain modeling expert.
    Help users build comprehensive domain models."""
)

agent.print_response("Help me model a library management system")
```

## Performance Considerations

- Entity extraction scales with description length
- Relationship mapping is O(n²) for n entities
- Use specific capabilities to reduce overhead
- Sample data parsing is lazy (only when needed)

## Future Enhancements

Planned features:
- Machine learning-based entity extraction
- Advanced business rule validation engine
- Code generation from domain models
- Database schema generation
- OpenAPI spec generation
- GraphQL schema generation

## Contributing

The Domain Analyzer FSA is part of the Agno Framework. Contributions are welcome!

## License

Part of the Agno Framework - see main project license.

## Support

For issues, questions, or feature requests, please refer to the Agno Framework documentation.
