"""Domain Analyzer FSA for the Agno Framework

PURPOSE: Analyze and understand domain-specific contexts, entities, relationships, and business logic
to provide intelligent domain modeling and reasoning capabilities.

KEY CAPABILITIES:
- Domain entity extraction and classification
- Relationship mapping and dependency analysis
- Business rule discovery and validation
- Domain vocabulary and ontology building
- Context-aware reasoning and inference
- Domain model generation and evolution
"""

import json
import re
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple

from agno.tools.toolkit import Toolkit
from agno.utils.log import logger


class DomainAnalyzer(Toolkit):
    """Domain Analyzer FSA - Analyzes domain contexts and generates intelligent domain models"""

    def __init__(
        self,
        name: str = "domain_analyzer",
        enable_entity_extraction: bool = True,
        enable_relationship_mapping: bool = True,
        enable_business_rules: bool = True,
        enable_ontology_building: bool = True,
        enable_reasoning: bool = True,
        enable_model_generation: bool = True,
        enable_validation: bool = True,
    ):
        """Initialize the Domain Analyzer FSA

        Args:
            name: Name of the toolkit
            enable_entity_extraction: Enable entity extraction and classification
            enable_relationship_mapping: Enable relationship mapping and dependency analysis
            enable_business_rules: Enable business rule discovery and validation
            enable_ontology_building: Enable domain vocabulary and ontology building
            enable_reasoning: Enable context-aware reasoning and inference
            enable_model_generation: Enable domain model generation
            enable_validation: Enable model validation capabilities
        """
        super().__init__(name=name)

        # State management
        self.domain_model: Dict[str, Any] = {
            "entities": {},
            "relationships": [],
            "business_rules": [],
            "vocabulary": {},
            "ontology": {},
            "metadata": {},
        }
        self.entity_cache: Dict[str, Dict[str, Any]] = {}
        self.relationship_graph: Dict[str, List[str]] = defaultdict(list)
        self.validation_results: Dict[str, Any] = {}

        # Register enabled capabilities
        if enable_entity_extraction:
            self.register(self.extract_entities)
            self.register(self.classify_entities)

        if enable_relationship_mapping:
            self.register(self.map_relationships)
            self.register(self.analyze_dependencies)

        if enable_business_rules:
            self.register(self.discover_business_rules)
            self.register(self.validate_business_rules)

        if enable_ontology_building:
            self.register(self.build_domain_ontology)
            self.register(self.extract_vocabulary)

        if enable_reasoning:
            self.register(self.infer_relationships)
            self.register(self.reason_about_domain)

        if enable_model_generation:
            self.register(self.generate_domain_model)
            self.register(self.evolve_domain_model)

        if enable_validation:
            self.register(self.validate_model)
            self.register(self.get_recommendations)

        # Always register core utility functions
        self.register(self.get_domain_model)
        self.register(self.reset_domain_model)

    def extract_entities(self, domain_description: str, sample_data: Optional[str] = None) -> str:
        """Extract entities from domain description and sample data

        Args:
            domain_description: Natural language description of the domain
            sample_data: Optional JSON string containing sample data from the domain

        Returns:
            str: JSON string containing extracted entities with their attributes
        """
        try:
            logger.info("Extracting entities from domain description")

            entities = {}

            # Extract entities from description using pattern matching
            # Look for capitalized words and common entity patterns
            entity_patterns = [
                r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:has|contains|includes|with)",
                r"(?:entity|object|class|type|model)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
                r"\b([A-Z][a-z]+)\s+(?:entity|object|class|model)",
            ]

            for pattern in entity_patterns:
                matches = re.findall(pattern, domain_description)
                for match in matches:
                    entity_name = match.strip()
                    if entity_name and entity_name not in entities:
                        entities[entity_name] = {
                            "name": entity_name,
                            "attributes": [],
                            "type": "unknown",
                            "source": "description",
                        }

            # Extract entities from sample data if provided
            if sample_data:
                try:
                    data = json.loads(sample_data)
                    self._extract_entities_from_data(data, entities)
                except json.JSONDecodeError:
                    logger.warning("Failed to parse sample_data as JSON")

            # Update domain model
            self.domain_model["entities"].update(entities)
            self.entity_cache.update(entities)

            result = {"entities": entities, "count": len(entities), "status": "success"}

            logger.debug(f"Extracted {len(entities)} entities")
            return json.dumps(result, indent=2)

        except Exception as e:
            logger.error(f"Error extracting entities: {e}")
            return json.dumps({"error": str(e), "status": "failed"}, indent=2)

    def _extract_entities_from_data(self, data: Any, entities: Dict[str, Any], parent_key: str = "") -> None:
        """Helper method to recursively extract entities from data structures"""
        if isinstance(data, dict):
            # Dictionary might represent an entity
            if parent_key and parent_key not in entities:
                entities[parent_key] = {
                    "name": parent_key,
                    "attributes": list(data.keys()),
                    "type": "object",
                    "source": "sample_data",
                }

            for key, value in data.items():
                # Capitalize key as potential entity name
                entity_name = key.replace("_", " ").title()
                if isinstance(value, dict):
                    self._extract_entities_from_data(value, entities, entity_name)
                elif isinstance(value, list) and value and isinstance(value[0], dict):
                    self._extract_entities_from_data(value[0], entities, entity_name)

        elif isinstance(data, list):
            if data and isinstance(data[0], dict):
                self._extract_entities_from_data(data[0], entities, parent_key)

    def classify_entities(self, entity_name: Optional[str] = None) -> str:
        """Classify entities into categories (e.g., aggregate, entity, value object)

        Args:
            entity_name: Optional specific entity to classify. If None, classifies all entities.

        Returns:
            str: JSON string containing entity classifications
        """
        try:
            logger.info(f"Classifying entities: {entity_name or 'all'}")

            classifications = {}
            entities_to_classify = (
                {entity_name: self.domain_model["entities"][entity_name]}
                if entity_name and entity_name in self.domain_model["entities"]
                else self.domain_model["entities"]
            )

            for name, entity in entities_to_classify.items():
                # Simple classification logic based on attributes and relationships
                classification = self._classify_entity(name, entity)
                classifications[name] = classification

                # Update entity in domain model
                self.domain_model["entities"][name]["classification"] = classification

            result = {"classifications": classifications, "count": len(classifications), "status": "success"}

            return json.dumps(result, indent=2)

        except Exception as e:
            logger.error(f"Error classifying entities: {e}")
            return json.dumps({"error": str(e), "status": "failed"}, indent=2)

    def _classify_entity(self, name: str, entity: Dict[str, Any]) -> str:
        """Helper method to classify a single entity"""
        # Check for common patterns
        attributes = entity.get("attributes", [])
        has_id = any("id" in str(attr).lower() for attr in attributes)
        has_many_attributes = len(attributes) > 5

        # Classification logic
        if has_id and has_many_attributes:
            return "aggregate_root"
        elif has_id:
            return "entity"
        elif len(attributes) <= 2:
            return "value_object"
        elif "service" in name.lower() or "manager" in name.lower():
            return "service"
        else:
            return "entity"

    def map_relationships(self, domain_description: str) -> str:
        """Map relationships between entities in the domain

        Args:
            domain_description: Natural language description of the domain with relationship information

        Returns:
            str: JSON string containing discovered relationships
        """
        try:
            logger.info("Mapping relationships between entities")

            relationships = []

            # Relationship patterns to detect
            relationship_patterns = [
                (r"([A-Z][a-z]+)\s+has\s+(?:many|multiple)\s+([A-Z][a-z]+)", "one_to_many"),
                (r"([A-Z][a-z]+)\s+has\s+(?:a|an|one)\s+([A-Z][a-z]+)", "one_to_one"),
                (r"([A-Z][a-z]+)\s+belongs\s+to\s+([A-Z][a-z]+)", "many_to_one"),
                (r"([A-Z][a-z]+)\s+contains\s+([A-Z][a-z]+)", "composition"),
                (r"([A-Z][a-z]+)\s+uses\s+([A-Z][a-z]+)", "dependency"),
                (r"([A-Z][a-z]+)\s+extends\s+([A-Z][a-z]+)", "inheritance"),
                (r"([A-Z][a-z]+)\s+implements\s+([A-Z][a-z]+)", "implementation"),
            ]

            for pattern, rel_type in relationship_patterns:
                matches = re.findall(pattern, domain_description, re.IGNORECASE)
                for match in matches:
                    source, target = match
                    relationship = {
                        "source": source.strip(),
                        "target": target.strip(),
                        "type": rel_type,
                        "bidirectional": False,
                    }
                    relationships.append(relationship)

                    # Update relationship graph
                    self.relationship_graph[relationship["source"]].append(relationship["target"])

            # Update domain model
            self.domain_model["relationships"].extend(relationships)

            result = {
                "relationships": relationships,
                "count": len(relationships),
                "graph": dict(self.relationship_graph),
                "status": "success",
            }

            logger.debug(f"Mapped {len(relationships)} relationships")
            return json.dumps(result, indent=2)

        except Exception as e:
            logger.error(f"Error mapping relationships: {e}")
            return json.dumps({"error": str(e), "status": "failed"}, indent=2)

    def analyze_dependencies(self) -> str:
        """Analyze dependencies between entities and identify potential issues

        Returns:
            str: JSON string containing dependency analysis results
        """
        try:
            logger.info("Analyzing entity dependencies")

            analysis = {
                "circular_dependencies": [],
                "coupling_score": {},
                "dependency_depth": {},
                "isolated_entities": [],
            }

            # Find circular dependencies
            visited = set()
            rec_stack = set()

            def has_cycle(node: str, path: List[str]) -> Optional[List[str]]:
                visited.add(node)
                rec_stack.add(node)

                for neighbor in self.relationship_graph.get(node, []):
                    if neighbor not in visited:
                        cycle = has_cycle(neighbor, path + [neighbor])
                        if cycle:
                            return cycle
                    elif neighbor in rec_stack:
                        # Found a cycle
                        cycle_start = path.index(neighbor)
                        return path[cycle_start:] + [neighbor]

                rec_stack.remove(node)
                return None

            # Check for cycles
            for entity in self.relationship_graph.keys():
                if entity not in visited:
                    cycle = has_cycle(entity, [entity])
                    if cycle:
                        analysis["circular_dependencies"].append(cycle)

            # Calculate coupling scores (number of dependencies)
            for entity, deps in self.relationship_graph.items():
                analysis["coupling_score"][entity] = len(deps)

            # Find isolated entities (no relationships)
            all_entities = set(self.domain_model["entities"].keys())
            connected_entities = set(self.relationship_graph.keys())
            analysis["isolated_entities"] = list(all_entities - connected_entities)

            result = {"analysis": analysis, "status": "success"}

            return json.dumps(result, indent=2)

        except Exception as e:
            logger.error(f"Error analyzing dependencies: {e}")
            return json.dumps({"error": str(e), "status": "failed"}, indent=2)

    def discover_business_rules(self, domain_description: str, existing_rules: Optional[str] = None) -> str:
        """Discover business rules and constraints from domain description

        Args:
            domain_description: Natural language description of the domain
            existing_rules: Optional JSON string of known business rules

        Returns:
            str: JSON string containing discovered business rules
        """
        try:
            logger.info("Discovering business rules")

            rules = []

            # Parse existing rules if provided
            if existing_rules:
                try:
                    rules = json.loads(existing_rules)
                except json.JSONDecodeError:
                    logger.warning("Failed to parse existing_rules as JSON")

            # Rule patterns to detect
            rule_patterns = [
                (r"must\s+(?:be|have|contain)\s+([^.]+)", "constraint"),
                (r"should\s+(?:be|have|contain)\s+([^.]+)", "recommendation"),
                (r"cannot\s+(?:be|have|contain)\s+([^.]+)", "prohibition"),
                (r"(?:if|when)\s+([^,]+),\s*(?:then)\s+([^.]+)", "conditional"),
                (r"always\s+([^.]+)", "invariant"),
                (r"never\s+([^.]+)", "prohibition"),
            ]

            for pattern, rule_type in rule_patterns:
                matches = re.findall(pattern, domain_description, re.IGNORECASE)
                for match in matches:
                    if isinstance(match, tuple):
                        rule_text = " ".join(match)
                    else:
                        rule_text = match

                    rule = {"type": rule_type, "description": rule_text.strip(), "status": "discovered"}
                    rules.append(rule)

            # Update domain model
            self.domain_model["business_rules"] = rules

            result = {"rules": rules, "count": len(rules), "status": "success"}

            logger.debug(f"Discovered {len(rules)} business rules")
            return json.dumps(result, indent=2)

        except Exception as e:
            logger.error(f"Error discovering business rules: {e}")
            return json.dumps({"error": str(e), "status": "failed"}, indent=2)

    def validate_business_rules(self, sample_data: str) -> str:
        """Validate business rules against sample data

        Args:
            sample_data: JSON string containing sample data to validate

        Returns:
            str: JSON string containing validation results
        """
        try:
            logger.info("Validating business rules against sample data")

            data = json.loads(sample_data)
            validation_results = {"passed": [], "failed": [], "skipped": []}

            for rule in self.domain_model["business_rules"]:
                # Basic validation logic (can be extended)
                rule_type = rule.get("type")
                description = rule.get("description", "")

                # Simple validation based on rule type
                if rule_type == "constraint":
                    # Check if constraint is satisfied
                    validation_results["skipped"].append(
                        {"rule": rule, "reason": "Automated validation not implemented for this rule type"}
                    )
                else:
                    validation_results["skipped"].append(
                        {"rule": rule, "reason": "Automated validation not implemented for this rule type"}
                    )

            result = {"validation_results": validation_results, "status": "success"}

            return json.dumps(result, indent=2)

        except Exception as e:
            logger.error(f"Error validating business rules: {e}")
            return json.dumps({"error": str(e), "status": "failed"}, indent=2)

    def build_domain_ontology(self, domain_description: str) -> str:
        """Build a domain ontology with hierarchical relationships

        Args:
            domain_description: Natural language description of the domain

        Returns:
            str: JSON string containing the domain ontology
        """
        try:
            logger.info("Building domain ontology")

            ontology = {"concepts": {}, "hierarchies": [], "properties": {}}

            # Extract key concepts (similar to entities but broader)
            concept_patterns = [
                r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+is\s+a\s+(?:type\s+of\s+)?([A-Z][a-z]+)",
                r"\b([A-Z][a-z]+)\s+(?:extends|inherits\s+from)\s+([A-Z][a-z]+)",
            ]

            for pattern in concept_patterns:
                matches = re.findall(pattern, domain_description)
                for match in matches:
                    child, parent = match
                    ontology["hierarchies"].append({"child": child.strip(), "parent": parent.strip()})

                    # Add concepts if not already present
                    for concept in [child.strip(), parent.strip()]:
                        if concept not in ontology["concepts"]:
                            ontology["concepts"][concept] = {"name": concept, "properties": []}

            # Update domain model
            self.domain_model["ontology"] = ontology

            result = {"ontology": ontology, "concepts_count": len(ontology["concepts"]), "status": "success"}

            logger.debug(f"Built ontology with {len(ontology['concepts'])} concepts")
            return json.dumps(result, indent=2)

        except Exception as e:
            logger.error(f"Error building ontology: {e}")
            return json.dumps({"error": str(e), "status": "failed"}, indent=2)

    def extract_vocabulary(self, domain_description: str) -> str:
        """Extract and define domain-specific vocabulary

        Args:
            domain_description: Natural language description of the domain

        Returns:
            str: JSON string containing domain vocabulary and definitions
        """
        try:
            logger.info("Extracting domain vocabulary")

            vocabulary = {}

            # Extract potential domain terms (capitalized phrases, technical terms)
            term_patterns = [
                r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:is|means|refers\s+to)\s+([^.]+)",
                r"(?:term|concept|definition):\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
            ]

            for pattern in term_patterns:
                matches = re.findall(pattern, domain_description)
                for match in matches:
                    if isinstance(match, tuple) and len(match) == 2:
                        term, definition = match
                        vocabulary[term.strip()] = {"definition": definition.strip(), "source": "description"}
                    else:
                        term = match
                        vocabulary[term.strip()] = {"definition": "No definition provided", "source": "description"}

            # Also include entity names in vocabulary
            for entity_name in self.domain_model["entities"].keys():
                if entity_name not in vocabulary:
                    vocabulary[entity_name] = {"definition": "Domain entity", "source": "entity_extraction"}

            # Update domain model
            self.domain_model["vocabulary"] = vocabulary

            result = {"vocabulary": vocabulary, "terms_count": len(vocabulary), "status": "success"}

            logger.debug(f"Extracted {len(vocabulary)} vocabulary terms")
            return json.dumps(result, indent=2)

        except Exception as e:
            logger.error(f"Error extracting vocabulary: {e}")
            return json.dumps({"error": str(e), "status": "failed"}, indent=2)

    def infer_relationships(self) -> str:
        """Infer additional relationships based on existing domain knowledge

        Returns:
            str: JSON string containing inferred relationships
        """
        try:
            logger.info("Inferring additional relationships")

            inferred_relationships = []

            # Infer relationships based on naming conventions
            for entity_name, entity in self.domain_model["entities"].items():
                attributes = entity.get("attributes", [])

                for attr in attributes:
                    # Check if attribute name suggests a relationship
                    attr_str = str(attr).lower()

                    # Look for foreign key patterns (e.g., user_id, customer_id)
                    if attr_str.endswith("_id") or attr_str.endswith("id"):
                        potential_target = attr_str.replace("_id", "").replace("id", "")
                        potential_target = potential_target.title()

                        # Check if potential target exists in entities
                        if potential_target in self.domain_model["entities"]:
                            relationship = {
                                "source": entity_name,
                                "target": potential_target,
                                "type": "many_to_one",
                                "inferred": True,
                                "basis": f"Foreign key attribute: {attr}",
                            }
                            inferred_relationships.append(relationship)

            # Add inferred relationships to domain model
            self.domain_model["relationships"].extend(inferred_relationships)

            result = {
                "inferred_relationships": inferred_relationships,
                "count": len(inferred_relationships),
                "status": "success",
            }

            logger.debug(f"Inferred {len(inferred_relationships)} relationships")
            return json.dumps(result, indent=2)

        except Exception as e:
            logger.error(f"Error inferring relationships: {e}")
            return json.dumps({"error": str(e), "status": "failed"}, indent=2)

    def reason_about_domain(self, query: str) -> str:
        """Perform context-aware reasoning about the domain

        Args:
            query: Natural language query about the domain

        Returns:
            str: JSON string containing reasoning results
        """
        try:
            logger.info(f"Reasoning about domain: {query}")

            reasoning_result = {
                "query": query,
                "relevant_entities": [],
                "relevant_relationships": [],
                "insights": [],
            }

            # Extract potential entity mentions from query
            query_lower = query.lower()
            for entity_name in self.domain_model["entities"].keys():
                if entity_name.lower() in query_lower:
                    reasoning_result["relevant_entities"].append(entity_name)

            # Find relevant relationships
            for rel in self.domain_model["relationships"]:
                if rel["source"] in reasoning_result["relevant_entities"] or rel[
                    "target"
                ] in reasoning_result["relevant_entities"]:
                    reasoning_result["relevant_relationships"].append(rel)

            # Generate insights
            if reasoning_result["relevant_entities"]:
                reasoning_result["insights"].append(
                    f"Found {len(reasoning_result['relevant_entities'])} relevant entities"
                )
            if reasoning_result["relevant_relationships"]:
                reasoning_result["insights"].append(
                    f"Found {len(reasoning_result['relevant_relationships'])} relevant relationships"
                )

            result = {"reasoning": reasoning_result, "status": "success"}

            return json.dumps(result, indent=2)

        except Exception as e:
            logger.error(f"Error reasoning about domain: {e}")
            return json.dumps({"error": str(e), "status": "failed"}, indent=2)

    def generate_domain_model(self, format: str = "json") -> str:
        """Generate a complete domain model in specified format

        Args:
            format: Output format (json, uml, diagram). Default is 'json'.

        Returns:
            str: Domain model in requested format
        """
        try:
            logger.info(f"Generating domain model in {format} format")

            if format.lower() == "json":
                result = {
                    "domain_model": self.domain_model,
                    "summary": {
                        "entities_count": len(self.domain_model["entities"]),
                        "relationships_count": len(self.domain_model["relationships"]),
                        "business_rules_count": len(self.domain_model["business_rules"]),
                        "vocabulary_terms": len(self.domain_model["vocabulary"]),
                    },
                    "status": "success",
                }
                return json.dumps(result, indent=2)

            elif format.lower() == "uml":
                # Generate PlantUML-style class diagram
                uml = ["@startuml", ""]

                # Add entities as classes
                for entity_name, entity in self.domain_model["entities"].items():
                    uml.append(f"class {entity_name} {{")
                    for attr in entity.get("attributes", []):
                        uml.append(f"  {attr}")
                    uml.append("}")
                    uml.append("")

                # Add relationships
                for rel in self.domain_model["relationships"]:
                    arrow = "-->"
                    if rel["type"] == "one_to_many":
                        arrow = "\"1\" --> \"*\""
                    elif rel["type"] == "one_to_one":
                        arrow = "\"1\" --> \"1\""
                    elif rel["type"] == "many_to_one":
                        arrow = "\"*\" --> \"1\""

                    uml.append(f"{rel['source']} {arrow} {rel['target']}")

                uml.append("")
                uml.append("@enduml")

                result = {"uml_diagram": "\n".join(uml), "format": "plantuml", "status": "success"}
                return json.dumps(result, indent=2)

            elif format.lower() == "diagram":
                # Generate a text-based diagram
                diagram = ["Domain Model Diagram", "=" * 50, ""]

                diagram.append("ENTITIES:")
                diagram.append("-" * 50)
                for entity_name in self.domain_model["entities"].keys():
                    diagram.append(f"  [{entity_name}]")

                diagram.append("\nRELATIONSHIPS:")
                diagram.append("-" * 50)
                for rel in self.domain_model["relationships"]:
                    diagram.append(f"  {rel['source']} --[{rel['type']}]--> {rel['target']}")

                result = {"diagram": "\n".join(diagram), "format": "text", "status": "success"}
                return json.dumps(result, indent=2)

            else:
                return json.dumps(
                    {"error": f"Unsupported format: {format}", "supported_formats": ["json", "uml", "diagram"]},
                    indent=2,
                )

        except Exception as e:
            logger.error(f"Error generating domain model: {e}")
            return json.dumps({"error": str(e), "status": "failed"}, indent=2)

    def evolve_domain_model(self, new_information: str) -> str:
        """Evolve the domain model based on new information

        Args:
            new_information: New domain information to incorporate

        Returns:
            str: JSON string containing evolution results
        """
        try:
            logger.info("Evolving domain model with new information")

            # Store current state for comparison
            previous_entity_count = len(self.domain_model["entities"])
            previous_relationship_count = len(self.domain_model["relationships"])

            # Extract new entities
            self.extract_entities(new_information)

            # Map new relationships
            self.map_relationships(new_information)

            # Discover new business rules
            self.discover_business_rules(new_information)

            # Extract new vocabulary
            self.extract_vocabulary(new_information)

            # Calculate changes
            changes = {
                "new_entities": len(self.domain_model["entities"]) - previous_entity_count,
                "new_relationships": len(self.domain_model["relationships"]) - previous_relationship_count,
                "total_entities": len(self.domain_model["entities"]),
                "total_relationships": len(self.domain_model["relationships"]),
            }

            result = {"changes": changes, "status": "success"}

            logger.debug(f"Domain model evolved: {changes}")
            return json.dumps(result, indent=2)

        except Exception as e:
            logger.error(f"Error evolving domain model: {e}")
            return json.dumps({"error": str(e), "status": "failed"}, indent=2)

    def validate_model(self, sample_data: Optional[str] = None) -> str:
        """Validate the domain model for consistency and completeness

        Args:
            sample_data: Optional JSON string with sample data to validate against

        Returns:
            str: JSON string containing validation results
        """
        try:
            logger.info("Validating domain model")

            validation_results = {
                "is_valid": True,
                "warnings": [],
                "errors": [],
                "suggestions": [],
            }

            # Check for entities without attributes
            for entity_name, entity in self.domain_model["entities"].items():
                if not entity.get("attributes"):
                    validation_results["warnings"].append(f"Entity '{entity_name}' has no attributes defined")

            # Check for isolated entities
            connected_entities = set()
            for rel in self.domain_model["relationships"]:
                connected_entities.add(rel["source"])
                connected_entities.add(rel["target"])

            isolated = set(self.domain_model["entities"].keys()) - connected_entities
            if isolated:
                validation_results["warnings"].append(
                    f"Isolated entities with no relationships: {', '.join(isolated)}"
                )

            # Check for circular dependencies
            analysis_result = self.analyze_dependencies()
            analysis = json.loads(analysis_result)
            if analysis.get("analysis", {}).get("circular_dependencies"):
                validation_results["errors"].append(
                    f"Circular dependencies detected: {analysis['analysis']['circular_dependencies']}"
                )
                validation_results["is_valid"] = False

            # Validate against sample data if provided
            if sample_data:
                try:
                    data = json.loads(sample_data)
                    # Check if data structure matches entity definitions
                    validation_results["suggestions"].append("Sample data validation not fully implemented")
                except json.JSONDecodeError:
                    validation_results["errors"].append("Sample data is not valid JSON")
                    validation_results["is_valid"] = False

            # Store validation results
            self.validation_results = validation_results

            result = {"validation": validation_results, "status": "success"}

            return json.dumps(result, indent=2)

        except Exception as e:
            logger.error(f"Error validating model: {e}")
            return json.dumps({"error": str(e), "status": "failed"}, indent=2)

    def get_recommendations(self) -> str:
        """Get recommendations for improving the domain model

        Returns:
            str: JSON string containing recommendations
        """
        try:
            logger.info("Generating recommendations")

            recommendations = []

            # Analyze entity count
            entity_count = len(self.domain_model["entities"])
            if entity_count == 0:
                recommendations.append(
                    {
                        "type": "missing_entities",
                        "priority": "high",
                        "description": "No entities defined. Start by extracting entities from domain description.",
                        "action": "Call extract_entities() with domain description",
                    }
                )
            elif entity_count < 3:
                recommendations.append(
                    {
                        "type": "few_entities",
                        "priority": "medium",
                        "description": "Only a few entities defined. Consider providing more domain information.",
                        "action": "Provide additional domain description or sample data",
                    }
                )

            # Analyze relationships
            relationship_count = len(self.domain_model["relationships"])
            if relationship_count == 0 and entity_count > 1:
                recommendations.append(
                    {
                        "type": "missing_relationships",
                        "priority": "high",
                        "description": "No relationships defined between entities.",
                        "action": "Call map_relationships() or infer_relationships()",
                    }
                )

            # Check for business rules
            if not self.domain_model["business_rules"]:
                recommendations.append(
                    {
                        "type": "missing_business_rules",
                        "priority": "medium",
                        "description": "No business rules defined.",
                        "action": "Call discover_business_rules() with domain constraints",
                    }
                )

            # Check for vocabulary
            if not self.domain_model["vocabulary"]:
                recommendations.append(
                    {
                        "type": "missing_vocabulary",
                        "priority": "low",
                        "description": "No domain vocabulary defined.",
                        "action": "Call extract_vocabulary() to build domain glossary",
                    }
                )

            # Check validation results if available
            if self.validation_results:
                if self.validation_results.get("errors"):
                    recommendations.append(
                        {
                            "type": "validation_errors",
                            "priority": "high",
                            "description": "Validation errors found in domain model.",
                            "action": "Review and fix validation errors",
                            "errors": self.validation_results["errors"],
                        }
                    )

            # Suggest model generation if not done yet
            if entity_count > 0 and relationship_count > 0:
                recommendations.append(
                    {
                        "type": "generate_model",
                        "priority": "medium",
                        "description": "Domain model ready for generation.",
                        "action": "Call generate_domain_model() to create final model",
                    }
                )

            result = {"recommendations": recommendations, "count": len(recommendations), "status": "success"}

            return json.dumps(result, indent=2)

        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            return json.dumps({"error": str(e), "status": "failed"}, indent=2)

    def get_domain_model(self) -> str:
        """Get the current domain model

        Returns:
            str: JSON string containing the complete domain model
        """
        try:
            result = {
                "domain_model": self.domain_model,
                "summary": {
                    "entities": len(self.domain_model["entities"]),
                    "relationships": len(self.domain_model["relationships"]),
                    "business_rules": len(self.domain_model["business_rules"]),
                    "vocabulary_terms": len(self.domain_model["vocabulary"]),
                },
                "status": "success",
            }
            return json.dumps(result, indent=2)

        except Exception as e:
            logger.error(f"Error getting domain model: {e}")
            return json.dumps({"error": str(e), "status": "failed"}, indent=2)

    def reset_domain_model(self) -> str:
        """Reset the domain model to empty state

        Returns:
            str: Confirmation message
        """
        try:
            self.domain_model = {
                "entities": {},
                "relationships": [],
                "business_rules": [],
                "vocabulary": {},
                "ontology": {},
                "metadata": {},
            }
            self.entity_cache = {}
            self.relationship_graph = defaultdict(list)
            self.validation_results = {}

            logger.info("Domain model reset successfully")
            return json.dumps({"message": "Domain model reset successfully", "status": "success"}, indent=2)

        except Exception as e:
            logger.error(f"Error resetting domain model: {e}")
            return json.dumps({"error": str(e), "status": "failed"}, indent=2)
