"""
Advanced Usage Examples for Multi-Agent HTML Generation System

This file demonstrates advanced usage patterns including:
1. Multiple provider configurations
2. Database integration with Qdrant
3. Batch generation
4. Custom agent modifications
5. Error handling and recovery
"""

import os
from html_generation_agent import (
    run_html_generation_workflow,
    LLMConfig,
    DatabaseConfig,
    build_graph,
    AgentState,
)


# =============================================================================
# EXAMPLE 1: Auto-Detect Best Provider
# =============================================================================

def example_1_auto_detect():
    """
    Automatically selects the best available LLM provider.
    Priority: OpenRouter > OpenAI > Anthropic
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 1: Auto-Detect LLM Provider")
    print("=" * 80)
    
    try:
        # Will auto-select provider based on available keys
        run_html_generation_workflow(
            "Create a simple portfolio page with hero, about, and contact sections"
        )
    except Exception as e:
        print(f"Error: {e}")


# =============================================================================
# EXAMPLE 2: Explicit Provider Selection
# =============================================================================

def example_2_explicit_provider():
    """
    Explicitly specify which LLM provider to use.
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 2: Explicit Provider Selection")
    print("=" * 80)
    
    providers_to_try = ["openrouter", "openai", "anthropic"]
    
    prompt = "Create a modern SaaS landing page with pricing table and feature highlights"
    
    for provider in providers_to_try:
        try:
            print(f"\nTrying with {LLMConfig.PROVIDERS.get(provider)}...")
            run_html_generation_workflow(prompt, llm_provider=provider)
            print(f"✓ Success with {provider}")
            break
        except ValueError as e:
            print(f"✗ {provider} not configured: {e}")
        except Exception as e:
            print(f"✗ Error with {provider}: {e}")


# =============================================================================
# EXAMPLE 3: Provider Availability Report
# =============================================================================

def example_3_check_providers():
    """
    Display configured providers and their details.
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 3: Provider Configuration Report")
    print("=" * 80)
    
    print("\n📡 Available LLM Providers:")
    print("-" * 80)
    
    providers_config = {
        "openai": {
            "env_var": "OPENAI_API_KEY",
            "description": "GPT-4 (highest quality)",
            "base_url": "https://api.openai.com/v1",
        },
        "openrouter": {
            "env_var": "OPENROUTER_API_KEY",
            "description": "GPT-4o-mini (best value)",
            "base_url": "https://openrouter.ai/api/v1",
        },
        "anthropic": {
            "env_var": "ANTHROPIC_API_KEY",
            "description": "Claude 3.5 Sonnet (excellent reasoning)",
            "base_url": "https://api.anthropic.com",
        },
    }
    
    for provider, config in providers_config.items():
        is_configured = bool(os.getenv(config["env_var"]))
        status = "✓ Configured" if is_configured else "✗ Not configured"
        print(f"\n{provider.upper()}")
        print(f"  Environment Variable: {config['env_var']}")
        print(f"  Description: {config['description']}")
        print(f"  Status: {status}")
    
    print("\n" + "-" * 80)
    print("📦 Database Configuration (Qdrant):")
    print("-" * 80)
    
    if DatabaseConfig.is_configured():
        print(f"✓ Qdrant URL: {os.getenv('QDRANT_URL')}")
        print(f"✓ Qdrant Collection: {os.getenv('QDRANT_COLLECTION')}")
        print("✓ Metadata storage: ENABLED")
    else:
        print("✗ Qdrant not configured")
        print("  To enable: Set QDRANT_URL and QDRANT_API_KEY in .env")


# =============================================================================
# EXAMPLE 4: Batch Generation with Different Providers
# =============================================================================

def example_4_batch_generation():
    """
    Generate multiple pages using different providers and track results.
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 4: Batch Generation with Provider Comparison")
    print("=" * 80)
    
    prompts = [
        "Create a tech blog landing page with featured articles section",
        "Create a restaurant website with menu and reservation form",
        "Create an e-commerce product page with reviews and related items",
    ]
    
    provider = "openrouter"  # Use cost-effective provider for batch
    
    for i, prompt in enumerate(prompts, 1):
        print(f"\n--- Batch {i}/{len(prompts)} ---")
        print(f"Prompt: {prompt[:60]}...")
        
        try:
            run_html_generation_workflow(
                prompt,
                llm_provider=provider,
                use_database=True,  # Store in Qdrant
            )
            print(f"✓ Generated successfully with {provider}")
        except Exception as e:
            print(f"✗ Failed: {e}")


# =============================================================================
# EXAMPLE 5: Database Integration (Qdrant)
# =============================================================================

def example_5_database_integration():
    """
    Demonstrate Qdrant database integration for metadata storage.
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 5: Database Integration with Qdrant")
    print("=" * 80)
    
    if not DatabaseConfig.is_configured():
        print("⚠️  Qdrant not configured")
        print("Set QDRANT_URL and QDRANT_API_KEY in .env to enable")
        return
    
    print("\n✓ Qdrant is configured")
    print("✓ Generation metadata will be stored automatically")
    print("\nStored metadata includes:")
    print("  - Timestamp of generation")
    print("  - User prompt and specifications")
    print("  - Framework choice (Tailwind/Bootstrap)")
    print("  - LLM provider used")
    print("  - HTML size and complexity")
    
    # Generate a page with database tracking
    try:
        run_html_generation_workflow(
            "Create a fitness app landing page",
            use_database=True,
        )
    except Exception as e:
        print(f"Error: {e}")


# =============================================================================
# EXAMPLE 6: Custom Prompt Engineering
# =============================================================================

def example_6_detailed_specification():
    """
    Demonstrate detailed prompt engineering for specific results.
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 6: Detailed Specification for Precise Output")
    print("=" * 80)
    
    detailed_prompt = """
Create a luxury watch brand landing page with these exact specifications:

STRUCTURE:
- Premium navigation with logo, menu items (Collections, About, Contact)
- Full-width hero section with product showcase
- Features section: 3 columns (Craftsmanship, Innovation, Heritage)
- Product showcase: 6 featured watches in 2x3 grid
- Testimonials: 2 customer quotes with star ratings
- Newsletter signup section
- Footer with links and copyright

DESIGN REQUIREMENTS:
- Color scheme: Elegant blacks, golds, and whites
- Typography: Serif fonts for headings, sans-serif for body
- Spacing: Generous whitespace and breathing room
- Interactive elements: Smooth hover effects on product cards
- Framework: Tailwind CSS for modern aesthetics

RESPONSIVENESS:
- Mobile-first approach
- Tablet (768px) and desktop (1024px+) optimized
- Touch-friendly buttons and interactions

ACCESSIBILITY:
- Proper heading hierarchy
- Alt text for all images
- Proper contrast ratios
- Semantic HTML structure
"""
    
    try:
        run_html_generation_workflow(
            detailed_prompt,
            llm_provider="openrouter",  # Use cost-effective provider
        )
        print("\n✓ Generated with detailed specifications")
    except Exception as e:
        print(f"Error: {e}")


# =============================================================================
# EXAMPLE 7: Provider Performance Comparison
# =============================================================================

def example_7_performance_comparison():
    """
    Compare generation results across multiple providers.
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 7: Provider Performance Comparison")
    print("=" * 80)
    
    prompt = "Create a portfolio website for a graphic designer"
    
    providers = ["openrouter", "openai", "anthropic"]
    results = {}
    
    for provider in providers:
        try:
            print(f"\nGenerating with {LLMConfig.PROVIDERS.get(provider)}...")
            
            # Would need to implement timing/tracking
            run_html_generation_workflow(
                prompt,
                llm_provider=provider,
            )
            
            # Get file info
            if os.path.exists("output.html"):
                file_size = os.path.getsize("output.html")
                results[provider] = {"size": file_size, "status": "success"}
                print(f"✓ Generated ({file_size} bytes)")
            
        except ValueError:
            results[provider] = {"status": "not_configured"}
            print(f"✗ Not configured")
        except Exception as e:
            results[provider] = {"status": "error", "error": str(e)}
            print(f"✗ Error: {e}")
    
    # Print comparison
    print("\n" + "-" * 80)
    print("COMPARISON RESULTS:")
    print("-" * 80)
    for provider, result in results.items():
        status = result.get("status", "unknown")
        if status == "success":
            print(f"{provider:12} - ✓ Success ({result['size']} bytes)")
        else:
            print(f"{provider:12} - ✗ {result.get('error', status)}")


# =============================================================================
# EXAMPLE 8: Error Handling and Recovery
# =============================================================================

def example_8_error_handling():
    """
    Demonstrate robust error handling and recovery.
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 8: Error Handling and Recovery")
    print("=" * 80)
    
    # Test with various problematic scenarios
    test_cases = [
        ("", "Empty prompt"),
        ("x", "Too short prompt"),
        ("Make a website about anything really", "Vague prompt (triggers clarification)"),
        ("Create a " + "very " * 500 + "long prompt", "Extremely long prompt"),
    ]
    
    for prompt, description in test_cases:
        print(f"\nTest: {description}")
        print(f"Prompt: {prompt[:60]}..." if len(prompt) > 60 else f"Prompt: {prompt}")
        
        try:
            # Would attempt generation with error handling
            run_html_generation_workflow(prompt, llm_provider="openrouter")
            print("✓ Handled successfully")
        except ValueError as e:
            print(f"✓ Caught validation error: {str(e)[:50]}...")
        except Exception as e:
            print(f"✓ Caught general error: {str(e)[:50]}...")


# =============================================================================
# EXAMPLE 9: Custom Workflow with Modified State
# =============================================================================

def example_9_custom_workflow():
    """
    Demonstrate custom workflow modifications.
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 9: Custom Workflow State Extension")
    print("=" * 80)
    
    print("""
This example shows how to:
1. Extend AgentState with custom fields
2. Modify node behavior
3. Add custom validation rules
4. Implement post-processing

Example modifications:

class ExtendedAgentState(AgentState):
    seo_metadata: dict
    performance_score: int
    accessibility_score: int
    
def validate_accessibility(state: AgentState) -> AgentState:
    # Add accessibility checks
    if 'alt=' not in state['html_content']:
        errors.append("Missing image alt attributes")
    return state

def validate_seo(state: AgentState) -> AgentState:
    # Add SEO checks
    if '<meta name="description"' not in state['html_content']:
        errors.append("Missing meta description")
    return state
""")


# =============================================================================
# EXAMPLE 10: Batch Processing with Cost Tracking
# =============================================================================

def example_10_cost_tracking():
    """
    Demonstrate cost-aware batch processing.
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 10: Cost-Aware Batch Processing")
    print("=" * 80)
    
    # Estimated costs per generation (approximate)
    costs = {
        "openai": 0.30,
        "openrouter": 0.02,
        "anthropic": 0.08,
    }
    
    num_pages = 10
    
    print(f"\nEstimated cost to generate {num_pages} pages:\n")
    
    for provider, cost_per_page in costs.items():
        if os.getenv(f"{'OPENAI_API_KEY' if provider == 'openai' else 'OPENROUTER_API_KEY' if provider == 'openrouter' else 'ANTHROPIC_API_KEY'}"):
            total_cost = cost_per_page * num_pages
            print(f"{provider:12} - ${cost_per_page:.2f}/page × {num_pages} = ${total_cost:.2f}")
        else:
            print(f"{provider:12} - Not configured")
    
    print("\n💡 Tip: Use OpenRouter for cost-effective batch processing")


# =============================================================================
# MAIN EXECUTION
# =============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("MULTI-AGENT HTML GENERATION - ADVANCED EXAMPLES")
    print("=" * 80)
    
    examples = [
        ("1", "Auto-Detect Provider", example_1_auto_detect),
        ("2", "Explicit Provider Selection", example_2_explicit_provider),
        ("3", "Provider Configuration Report", example_3_check_providers),
        ("4", "Batch Generation", example_4_batch_generation),
        ("5", "Database Integration", example_5_database_integration),
        ("6", "Detailed Specification", example_6_detailed_specification),
        ("7", "Performance Comparison", example_7_performance_comparison),
        ("8", "Error Handling", example_8_error_handling),
        ("9", "Custom Workflow", example_9_custom_workflow),
        ("10", "Cost Tracking", example_10_cost_tracking),
    ]
    
    print("\n📚 Available Examples:")
    print("-" * 80)
    for num, title, _ in examples:
        print(f"  {num:2} - {title}")
    
    print("\nUsage: python examples.py <number>")
    print("Example: python examples.py 3")
    
    # Uncomment to run specific example:
    # example_3_check_providers()
    
    # Or run all examples:
    # for _, _, func in examples:
    #     try:
    #         func()
    #     except KeyboardInterrupt:
    #         break
    #     except Exception as e:
    #         print(f"Error: {e}")
