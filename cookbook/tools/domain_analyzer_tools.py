"""
Example demonstrating the Domain Analyzer FSA for the Agno Framework

This example shows how to use the Domain Analyzer to:
- Extract entities from domain descriptions
- Map relationships between entities
- Discover business rules
- Build domain ontologies
- Generate domain models
"""

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.domain_analyzer import DomainAnalyzer

# Example domain description for an e-commerce system
domain_description = """
An e-commerce platform where Customer can place multiple Orders.
Each Order contains one or more OrderItems. An OrderItem references a Product.
A Product belongs to a Category. Customer has a ShoppingCart that contains Products.
A Customer must have a valid email address and cannot place orders without payment information.
Orders should be processed within 24 hours. A Product cannot be sold if it's out of stock.
Payment is a value object that contains payment method and billing information.
Order is an aggregate root that manages OrderItems.
"""

# Example sample data
sample_data = """
{
  "customer": {
    "id": 1,
    "email": "customer@example.com",
    "name": "John Doe",
    "address": "123 Main St"
  },
  "order": {
    "id": 1001,
    "customer_id": 1,
    "status": "pending",
    "total": 99.99,
    "items": [
      {
        "product_id": 501,
        "quantity": 2,
        "price": 49.99
      }
    ]
  },
  "product": {
    "id": 501,
    "name": "Widget",
    "category_id": 10,
    "price": 49.99,
    "stock": 100
  }
}
"""

# Create Domain Analyzer with all capabilities enabled
domain_analyzer = DomainAnalyzer(
    name="ecommerce_domain_analyzer",
    enable_entity_extraction=True,
    enable_relationship_mapping=True,
    enable_business_rules=True,
    enable_ontology_building=True,
    enable_reasoning=True,
    enable_model_generation=True,
    enable_validation=True,
)

# Create an agent with the Domain Analyzer
agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    tools=[domain_analyzer],
    show_tool_calls=True,
    markdown=True,
    instructions="""You are a domain modeling expert assistant.
    Help analyze the e-commerce domain and create a comprehensive domain model.
    Use the domain_analyzer tools to extract entities, map relationships, and generate insights.""",
)

# Example 1: Basic Domain Analysis
print("=" * 80)
print("EXAMPLE 1: Basic Domain Analysis")
print("=" * 80)
agent.print_response(
    f"""Analyze this e-commerce domain description and extract all entities:

{domain_description}

Also use this sample data to enhance your analysis:
{sample_data}
""",
    stream=False,
)

# Example 2: Relationship Mapping
print("\n" + "=" * 80)
print("EXAMPLE 2: Map Entity Relationships")
print("=" * 80)
agent.print_response(
    f"""Map all the relationships between entities in this domain:

{domain_description}
""",
    stream=False,
)

# Example 3: Business Rules Discovery
print("\n" + "=" * 80)
print("EXAMPLE 3: Discover Business Rules")
print("=" * 80)
agent.print_response(
    f"""Discover and list all business rules and constraints from this domain description:

{domain_description}
""",
    stream=False,
)

# Example 4: Complete Domain Model Generation
print("\n" + "=" * 80)
print("EXAMPLE 4: Generate Complete Domain Model")
print("=" * 80)
agent.print_response(
    """Generate a complete domain model in UML format showing all entities,
    their relationships, and provide recommendations for improvement.""",
    stream=False,
)

# Example 5: Domain Reasoning
print("\n" + "=" * 80)
print("EXAMPLE 5: Reason About Domain")
print("=" * 80)
agent.print_response(
    """What entities and relationships are involved when a Customer places an Order?
    Use the domain analyzer to reason about this scenario.""",
    stream=False,
)

# Example 6: Validate Domain Model
print("\n" + "=" * 80)
print("EXAMPLE 6: Validate Domain Model")
print("=" * 80)
agent.print_response(
    f"""Validate the domain model against this sample data and provide recommendations:

{sample_data}
""",
    stream=False,
)

# Example 7: Simple workflow - no agent
print("\n" + "=" * 80)
print("EXAMPLE 7: Direct Tool Usage (Without Agent)")
print("=" * 80)

# Create a standalone domain analyzer
standalone_analyzer = DomainAnalyzer()

# Extract entities
print("\n1. Extracting entities...")
result = standalone_analyzer.extract_entities(domain_description, sample_data)
print(result)

# Map relationships
print("\n2. Mapping relationships...")
result = standalone_analyzer.map_relationships(domain_description)
print(result)

# Discover business rules
print("\n3. Discovering business rules...")
result = standalone_analyzer.discover_business_rules(domain_description)
print(result)

# Build ontology
print("\n4. Building domain ontology...")
result = standalone_analyzer.build_domain_ontology(domain_description)
print(result)

# Extract vocabulary
print("\n5. Extracting vocabulary...")
result = standalone_analyzer.extract_vocabulary(domain_description)
print(result)

# Classify entities
print("\n6. Classifying entities...")
result = standalone_analyzer.classify_entities()
print(result)

# Infer additional relationships
print("\n7. Inferring relationships...")
result = standalone_analyzer.infer_relationships()
print(result)

# Analyze dependencies
print("\n8. Analyzing dependencies...")
result = standalone_analyzer.analyze_dependencies()
print(result)

# Validate model
print("\n9. Validating model...")
result = standalone_analyzer.validate_model(sample_data)
print(result)

# Get recommendations
print("\n10. Getting recommendations...")
result = standalone_analyzer.get_recommendations()
print(result)

# Generate final domain model
print("\n11. Generating domain model (JSON)...")
result = standalone_analyzer.generate_domain_model("json")
print(result)

print("\n12. Generating domain model (UML)...")
result = standalone_analyzer.generate_domain_model("uml")
print(result)

print("\n13. Generating domain model (Diagram)...")
result = standalone_analyzer.generate_domain_model("diagram")
print(result)

# Example 8: Domain Model Evolution
print("\n" + "=" * 80)
print("EXAMPLE 8: Evolving Domain Model with New Information")
print("=" * 80)

new_domain_info = """
The e-commerce platform now supports Wishlists. A Customer can have multiple Wishlists.
Each Wishlist contains Products. A Product can be in multiple Wishlists.
Customers can share Wishlists with other Customers.
A Wishlist must have a name and cannot be empty for more than 30 days.
"""

print("Adding new domain information:")
print(new_domain_info)
result = standalone_analyzer.evolve_domain_model(new_domain_info)
print("\nEvolution result:")
print(result)

# Example 9: Custom Configuration
print("\n" + "=" * 80)
print("EXAMPLE 9: Custom Domain Analyzer Configuration")
print("=" * 80)

# Create analyzer with only specific capabilities
custom_analyzer = DomainAnalyzer(
    name="custom_analyzer",
    enable_entity_extraction=True,
    enable_relationship_mapping=True,
    enable_business_rules=False,  # Disabled
    enable_ontology_building=False,  # Disabled
    enable_reasoning=False,  # Disabled
    enable_model_generation=True,
    enable_validation=True,
)

custom_agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    tools=[custom_analyzer],
    show_tool_calls=True,
    markdown=True,
    instructions="You are a focused domain modeling assistant. You only extract entities and map relationships.",
)

print("This agent has a limited set of domain analysis capabilities.")
custom_agent.print_response(
    f"""Analyze this domain and extract entities with their relationships:

{domain_description}
""",
    stream=False,
)

print("\n" + "=" * 80)
print("Domain Analysis Complete!")
print("=" * 80)
