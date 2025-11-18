"""
Example Usage: Duplication Detector FSA

Demonstrates comprehensive code clone detection across multiple samples
with refactoring recommendations.
"""

from duplication_detector import (
    DuplicationDetector,
    CloneType,
    CodeLocation
)


def main():
    """Demonstrate duplication detection with various code samples"""

    print("=" * 80)
    print("DUPLICATION DETECTOR FSA - Example Usage")
    print("=" * 80)
    print()

    # Initialize detector
    detector = DuplicationDetector(
        min_tokens=15,
        min_lines=4,
        similarity_threshold=0.75,
        enable_type_4=True
    )

    # Sample code with various types of duplication
    sample_codes = [
        # Code Sample 1: User authentication
        """
def authenticate_user(username, password):
    if not username or not password:
        return False
    user = database.find_user(username)
    if not user:
        return False
    if not verify_password(password, user.password_hash):
        return False
    return True
""",
        # Code Sample 2: Admin authentication (exact duplicate with renames)
        """
def authenticate_admin(admin_name, admin_pass):
    if not admin_name or not admin_pass:
        return False
    admin = database.find_user(admin_name)
    if not admin:
        return False
    if not verify_password(admin_pass, admin.password_hash):
        return False
    return True
""",
        # Code Sample 3: Email validation
        """
def validate_email_address(email):
    if not email:
        return False
    if '@' not in email:
        return False
    if '.' not in email.split('@')[1]:
        return False
    return True
""",
        # Code Sample 4: Phone validation (similar structure)
        """
def validate_phone_number(phone):
    if not phone:
        return False
    if len(phone) < 10:
        return False
    if not phone.replace('-', '').isdigit():
        return False
    return True
""",
        # Code Sample 5: Data processing
        """
def process_user_data(users):
    results = []
    for user in users:
        if user.active:
            processed = {
                'id': user.id,
                'name': user.name,
                'email': user.email
            }
            results.append(processed)
    return results
""",
        # Code Sample 6: Product processing (Type-2 clone)
        """
def process_product_data(products):
    output = []
    for product in products:
        if product.active:
            item = {
                'id': product.id,
                'name': product.name,
                'email': product.email
            }
            output.append(item)
    return output
""",
        # Code Sample 7: Calculate total with tax
        """
def calculate_order_total(items, tax_rate):
    subtotal = 0
    for item in items:
        subtotal += item.price * item.quantity
    tax = subtotal * tax_rate
    total = subtotal + tax
    return total
""",
        # Code Sample 8: Calculate invoice (semantic clone)
        """
def compute_invoice_amount(line_items, tax_percentage):
    base_amount = sum(li.price * li.qty for li in line_items)
    tax_amount = base_amount * tax_percentage
    return base_amount + tax_amount
"""
    ]

    print("Analyzing {} code samples for duplicates...\n".format(len(sample_codes)))

    # Run duplication detection
    report = detector.detect_duplicates(sample_codes)

    # Display Results
    print("-" * 80)
    print("DETECTION RESULTS")
    print("-" * 80)
    print()

    # Overall Metrics
    print("📊 CLONE METRICS:")
    print(f"  Total Clones Found: {report.metrics.total_clones}")
    print(f"  Clone Coverage: {report.metrics.clone_coverage:.2f}%")
    print(f"  Clone Density: {report.metrics.clone_density:.2f} per KLOC")
    print(f"  Largest Clone: {report.metrics.largest_clone_size} lines")
    print(f"  Total Duplicated Lines: {report.metrics.total_duplicated_lines}")
    print()

    # Clone Type Distribution
    print("📈 CLONE TYPE DISTRIBUTION:")
    for clone_type, count in report.metrics.clone_type_distribution.items():
        print(f"  {clone_type.value.upper()}: {count} clones")
    print()

    # Detailed Clone Information
    if report.clones:
        print("-" * 80)
        print("🔍 DETECTED CLONES (Top 5):")
        print("-" * 80)
        print()

        for idx, clone in enumerate(report.clones[:5], 1):
            print(f"Clone #{idx}:")
            print(f"  Type: {clone.clone_type.value.upper()}")
            print(f"  Similarity: {clone.similarity:.2%}")
            print(f"  Size: {clone.size()} lines, {clone.token_count} tokens")
            print(f"  Location 1: {clone.location1}")
            print(f"  Location 2: {clone.location2}")

            # Show code preview
            print(f"  Code Preview 1:")
            preview1 = '\n'.join(clone.code1.split('\n')[:3])
            for line in preview1.split('\n'):
                print(f"    {line}")

            print(f"  Code Preview 2:")
            preview2 = '\n'.join(clone.code2.split('\n')[:3])
            for line in preview2.split('\n'):
                print(f"    {line}")

            # Type-specific information
            if clone.clone_type == CloneType.TYPE_2:
                if hasattr(clone, 'identifier_mapping') and clone.identifier_mapping:
                    print(f"  Identifier Mappings:")
                    for old, new in list(clone.identifier_mapping.items())[:3]:
                        print(f"    {old} → {new}")

            elif clone.clone_type == CloneType.TYPE_3:
                if hasattr(clone, 'edit_distance'):
                    print(f"  Edit Distance: {clone.edit_distance}")

            elif clone.clone_type == CloneType.TYPE_4:
                if hasattr(clone, 'equivalence_proof'):
                    print(f"  Equivalence: {clone.equivalence_proof}")

            print()

    # Clone Clusters
    if report.clusters:
        print("-" * 80)
        print("📦 CLONE CLUSTERS:")
        print("-" * 80)
        print()

        for idx, cluster in enumerate(report.clusters[:3], 1):
            print(f"Cluster #{idx}:")
            print(f"  Size: {cluster.size()} clones")
            print(f"  Total Duplicated Lines: {cluster.total_duplicated_lines()}")
            print(f"  Affected Files: {len(cluster.affected_files)}")
            if cluster.affected_files:
                for file in list(cluster.affected_files)[:3]:
                    print(f"    - {file}")
            print()

    # Refactoring Recommendations
    if report.recommendations:
        print("-" * 80)
        print("💡 REFACTORING RECOMMENDATIONS:")
        print("-" * 80)
        print()

        for idx, suggestion in enumerate(report.recommendations[:5], 1):
            print(f"Recommendation #{idx}:")
            print(f"  Type: {suggestion.refactoring_type.value.upper().replace('_', ' ')}")
            print(f"  Confidence: {suggestion.confidence:.0%}")
            print(f"  Description: {suggestion.description}")
            print(f"  Benefit: {suggestion.benefit}")
            print(f"  Estimated LOC Reduction: {suggestion.estimated_loc_reduction} lines")
            print()

    # Summary and Analysis
    print("-" * 80)
    print("📋 SUMMARY & ANALYSIS:")
    print("-" * 80)
    print()

    if report.metrics.clone_coverage > 15:
        print("⚠️  HIGH DUPLICATION DETECTED!")
        print(f"   Your code has {report.metrics.clone_coverage:.1f}% duplication.")
        print("   Recommended: Implement refactoring suggestions to reduce duplication.")
    elif report.metrics.clone_coverage > 5:
        print("⚡ MODERATE DUPLICATION")
        print(f"   Your code has {report.metrics.clone_coverage:.1f}% duplication.")
        print("   Consider refactoring high-priority clones.")
    else:
        print("✅ LOW DUPLICATION")
        print(f"   Your code has {report.metrics.clone_coverage:.1f}% duplication.")
        print("   Code duplication is within acceptable limits.")

    print()

    # Type-specific insights
    type_dist = report.metrics.clone_type_distribution

    if CloneType.TYPE_1 in type_dist and type_dist[CloneType.TYPE_1] > 0:
        print(f"📌 Found {type_dist[CloneType.TYPE_1]} exact clones (Type-1)")
        print("   These are identical code blocks that can be easily extracted into functions.")
        print()

    if CloneType.TYPE_2 in type_dist and type_dist[CloneType.TYPE_2] > 0:
        print(f"📌 Found {type_dist[CloneType.TYPE_2]} renamed clones (Type-2)")
        print("   These have renamed variables/functions but same structure.")
        print("   Consider parameterizing the differences.")
        print()

    if CloneType.TYPE_3 in type_dist and type_dist[CloneType.TYPE_3] > 0:
        print(f"📌 Found {type_dist[CloneType.TYPE_3]} structural clones (Type-3)")
        print("   These have similar structure with minor modifications.")
        print("   May require template method pattern or strategy pattern.")
        print()

    if CloneType.TYPE_4 in type_dist and type_dist[CloneType.TYPE_4] > 0:
        print(f"📌 Found {type_dist[CloneType.TYPE_4]} semantic clones (Type-4)")
        print("   These implement same functionality differently.")
        print("   Review for consistency and standardization.")
        print()

    # Action items
    print("🎯 RECOMMENDED ACTIONS:")
    if report.recommendations:
        priority_actions = sorted(
            report.recommendations,
            key=lambda r: r.estimated_loc_reduction,
            reverse=True
        )[:3]

        for idx, action in enumerate(priority_actions, 1):
            print(f"  {idx}. {action.description}")
            print(f"     Impact: Save {action.estimated_loc_reduction} lines")
    else:
        print("  No specific refactoring needed at this time.")

    print()
    print("=" * 80)
    print("Analysis complete!")
    print("=" * 80)


def example_incremental_detection():
    """Example: Incremental detection for large codebases"""

    print("\n" + "=" * 80)
    print("INCREMENTAL DETECTION EXAMPLE")
    print("=" * 80)
    print()

    detector = DuplicationDetector(min_tokens=20, min_lines=5)

    # Simulate analyzing a file
    code = """
def calculate_discount(price, discount_rate):
    if discount_rate <= 0:
        return price
    discount_amount = price * discount_rate
    final_price = price - discount_amount
    return final_price
"""

    print("Analyzing code for duplicates...")
    report = detector.detect_duplicates(code)

    print(f"Found {report.metrics.total_clones} clones")
    print(f"Clone coverage: {report.metrics.clone_coverage:.2f}%")


def example_visualization():
    """Example: Preparing data for visualization"""

    print("\n" + "=" * 80)
    print("VISUALIZATION EXAMPLE")
    print("=" * 80)
    print()

    from pathlib import Path
    import tempfile

    detector = DuplicationDetector()

    code_samples = [
        "def func1():\n    return 42",
        "def func2():\n    return 42"
    ]

    report = detector.detect_duplicates(code_samples)

    # Generate visualization data
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        output_path = Path(f.name)

    success = detector.visualize_clones(report.clones, output_path)

    if success:
        print(f"✅ Visualization data saved to: {output_path}")
        print("   Use this data to create heatmaps or scatter plots")
    else:
        print("❌ Failed to generate visualization data")


if __name__ == "__main__":
    # Run main example
    main()

    # Additional examples
    example_incremental_detection()
    example_visualization()
