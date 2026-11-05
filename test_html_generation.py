"""
Test runner for the HTML generation system.
This version includes mock LLM responses for testing without requiring OpenAI API key.
"""

import sys
from typing import Optional
from html_generation_agent import (
    build_graph,
    AgentState,
    START,
    END,
)


def mock_test_workflow():
    """
    Test the workflow with a simple clear requirement.
    Uses mock state progression to demonstrate the graph.
    """
    print("\n" + "=" * 80)
    print("🧪 TESTING HTML GENERATION WORKFLOW")
    print("=" * 80)

    # Create a mock state with all nodes' outputs pre-filled
    # This demonstrates the full workflow without needing API calls
    test_state: AgentState = {
        "user_prompt": "Create a modern landing page for a tech startup that sells AI tools. Include a hero section, features grid, testimonials, and a contact form.",
        "manager_clarifications": [],
        "final_specifications": """
FINAL SPECIFICATIONS:
- Landing Page for AI Tools Tech Startup
- Hero Section: Catchy headline + CTA button
- Features Grid: 3 features (Lightning Fast, Secure, Scalable)
- Testimonials: 2 customer quotes
- Contact Form: Name, Email, Message fields
- Design: Dark theme with blue and emerald accents
- Framework: Tailwind CSS recommended for modern look
""",
        "ux_blueprint": """
UX BLUEPRINT:
1. Navigation Bar
   - Logo on left
   - Menu items (Features, Testimonials, Contact)
   - Right-aligned CTA

2. Hero Section
   - Full-width gradient background
   - Large headline (5xl)
   - Subheading
   - CTA button

3. Features Section
   - Grid layout (3 columns on desktop, 1 on mobile)
   - Feature cards with icons
   - Each card: Icon, Title, Description

4. Testimonials Section
   - 2-column grid
   - Quote cards with author info
   - Left border accent

5. Contact Section
   - Contact form (Name, Email, Message)
   - Centered layout
   - Submit button

6. Footer
   - Copyright text
   - Centered
""",
        "design_system": """
DESIGN SYSTEM:
Color Palette:
- Primary Background: #0f172a (slate-900)
- Secondary Background: #1e293b (slate-800)
- Tertiary Background: #334155 (slate-700)
- Primary Accent: #3B82F6 (blue-500)
- Secondary Accent: #10B981 (emerald-500)
- Text Primary: #ffffff (white)
- Text Secondary: #cbd5e1 (slate-300)

Typography:
- Headlines: Bold, sans-serif
- Body: Regular, sans-serif
- Hero H1: 3rem (48px)
- Section H2: 1.875rem (30px)
- Body text: 1rem (16px)

Spacing:
- Section padding: 4rem vertical
- Container max-width: 64rem (1024px)
- Gap between grid items: 2rem

Component Classes (Tailwind):
- Button: bg-blue-500 hover:bg-blue-600 text-white px-8 py-3 rounded-lg
- Card: bg-slate-700 p-6 rounded-lg
- Input: bg-slate-600 text-white px-4 py-2 rounded
- Section: py-16 px-4
""",
        "framework_choice": "Tailwind",
        "html_content": """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Tools - Modern AI Solutions</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-900 text-white">
    <!-- Navigation -->
    <nav class="bg-slate-800 border-b border-slate-700 sticky top-0 z-50">
        <div class="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
            <div class="text-2xl font-bold text-blue-400">AI Tools</div>
            <div class="space-x-6 hidden md:flex">
                <a href="#features" class="hover:text-blue-400 transition">Features</a>
                <a href="#testimonials" class="hover:text-blue-400 transition">Testimonials</a>
                <a href="#contact" class="hover:text-blue-400 transition">Contact</a>
            </div>
            <button class="md:hidden text-blue-400">☰</button>
        </div>
    </nav>

    <!-- Hero Section -->
    <section class="bg-gradient-to-b from-slate-900 via-blue-900 to-slate-900 py-24">
        <div class="max-w-6xl mx-auto px-4 text-center">
            <h1 class="text-5xl md:text-6xl font-bold mb-6 text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-emerald-400">
                Powerful AI Tools for Your Business
            </h1>
            <p class="text-xl text-slate-300 mb-8 max-w-2xl mx-auto">
                Transform your workflows with cutting-edge artificial intelligence. Automate tasks, gain insights, and scale effortlessly.
            </p>
            <div class="flex gap-4 justify-center">
                <button class="bg-blue-500 hover:bg-blue-600 text-white px-8 py-3 rounded-lg font-semibold transition">
                    Get Started Free
                </button>
                <button class="border-2 border-blue-500 text-blue-400 hover:bg-blue-500 hover:text-white px-8 py-3 rounded-lg font-semibold transition">
                    Learn More
                </button>
            </div>
        </div>
    </section>

    <!-- Features Section -->
    <section id="features" class="py-20 bg-slate-800">
        <div class="max-w-6xl mx-auto px-4">
            <h2 class="text-4xl font-bold text-center mb-16">Why Choose Our AI Tools?</h2>
            <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
                <!-- Feature 1 -->
                <div class="bg-slate-700 p-8 rounded-lg hover:shadow-lg hover:shadow-blue-500/20 transition">
                    <div class="text-5xl mb-4">⚡</div>
                    <h3 class="text-2xl font-bold mb-3">Lightning Fast</h3>
                    <p class="text-slate-300 leading-relaxed">Process data in milliseconds with our optimized algorithms. Get results instantly without waiting.</p>
                </div>
                <!-- Feature 2 -->
                <div class="bg-slate-700 p-8 rounded-lg hover:shadow-lg hover:shadow-emerald-500/20 transition">
                    <div class="text-5xl mb-4">🔒</div>
                    <h3 class="text-2xl font-bold mb-3">Enterprise Secure</h3>
                    <p class="text-slate-300 leading-relaxed">Bank-grade security with end-to-end encryption. Your data is always protected and compliant.</p>
                </div>
                <!-- Feature 3 -->
                <div class="bg-slate-700 p-8 rounded-lg hover:shadow-lg hover:shadow-blue-500/20 transition">
                    <div class="text-5xl mb-4">📊</div>
                    <h3 class="text-2xl font-bold mb-3">Infinitely Scalable</h3>
                    <p class="text-slate-300 leading-relaxed">Grow from startup to enterprise. Our infrastructure scales automatically with your needs.</p>
                </div>
            </div>
        </div>
    </section>

    <!-- Testimonials Section -->
    <section id="testimonials" class="py-20 bg-slate-900">
        <div class="max-w-6xl mx-auto px-4">
            <h2 class="text-4xl font-bold text-center mb-16">What Our Customers Say</h2>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
                <!-- Testimonial 1 -->
                <div class="bg-slate-800 p-8 rounded-lg border-l-4 border-blue-500">
                    <div class="flex items-center mb-4">
                        <div class="text-yellow-400">⭐⭐⭐⭐⭐</div>
                    </div>
                    <p class="text-slate-300 mb-6 italic">"This tool completely transformed our workflow. We've cut processing time by 80% and our team is way more productive. Highly recommended!"</p>
                    <p class="font-semibold text-blue-400">Sarah Chen</p>
                    <p class="text-slate-400 text-sm">CTO at TechCorp</p>
                </div>
                <!-- Testimonial 2 -->
                <div class="bg-slate-800 p-8 rounded-lg border-l-4 border-emerald-500">
                    <div class="flex items-center mb-4">
                        <div class="text-yellow-400">⭐⭐⭐⭐⭐</div>
                    </div>
                    <p class="text-slate-300 mb-6 italic">"The best investment we made this year. ROI was immediate and the support team is phenomenal. A game-changer for our business."</p>
                    <p class="font-semibold text-emerald-400">Michael Rodriguez</p>
                    <p class="text-slate-400 text-sm">CEO at StartupXYZ</p>
                </div>
            </div>
        </div>
    </section>

    <!-- Contact Section -->
    <section id="contact" class="py-20 bg-slate-800">
        <div class="max-w-2xl mx-auto px-4">
            <h2 class="text-4xl font-bold text-center mb-12">Get In Touch</h2>
            <form class="bg-slate-700 p-12 rounded-lg space-y-6">
                <div>
                    <label class="block text-sm font-semibold mb-2">Full Name</label>
                    <input type="text" placeholder="John Doe" class="w-full bg-slate-600 text-white px-4 py-3 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500">
                </div>
                <div>
                    <label class="block text-sm font-semibold mb-2">Email Address</label>
                    <input type="email" placeholder="john@example.com" class="w-full bg-slate-600 text-white px-4 py-3 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500">
                </div>
                <div>
                    <label class="block text-sm font-semibold mb-2">Message</label>
                    <textarea placeholder="Tell us about your project..." rows="6" class="w-full bg-slate-600 text-white px-4 py-3 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"></textarea>
                </div>
                <button type="submit" class="w-full bg-blue-500 hover:bg-blue-600 text-white px-6 py-3 rounded-lg font-semibold transition">
                    Send Message
                </button>
            </form>
        </div>
    </section>

    <!-- Footer -->
    <footer class="bg-slate-900 border-t border-slate-700 py-8 text-center text-slate-400">
        <p>&copy; 2024 AI Tools Platform. All rights reserved. | Privacy Policy | Terms of Service</p>
    </footer>
</body>
</html>""",
        "validation_errors": [],
        "retry_count": 0,
    }

    print("\n✓ Mock state created with all agent outputs pre-filled")
    print(f"  - User Prompt: {test_state['user_prompt'][:60]}...")
    print(f"  - Framework: {test_state['framework_choice']}")
    print(f"  - HTML Size: {len(test_state['html_content'])} bytes")

    return test_state


def validate_html_structure(html_content: str) -> dict:
    """
    Validate the structure of generated HTML.
    """
    print("\n" + "-" * 80)
    print("Validating HTML Structure")
    print("-" * 80)

    errors = []
    warnings = []

    # Check DOCTYPE
    if "<!DOCTYPE html>" not in html_content:
        errors.append("Missing <!DOCTYPE html>")

    # Check HTML tags
    if "<html" not in html_content:
        errors.append("Missing <html> tag")
    if "</html>" not in html_content:
        errors.append("Missing closing </html> tag")

    # Check head and body
    if "<head" not in html_content:
        errors.append("Missing <head> tag")
    if "<body" not in html_content:
        errors.append("Missing <body> tag")

    # Check for CDN links
    if "cdn.tailwindcss.com" not in html_content and "bootstrap" not in html_content.lower():
        errors.append("Missing CSS framework CDN link")

    # Check for markdown code blocks
    if "```" in html_content:
        errors.append("HTML contains markdown code blocks (```)")

    # Warnings
    if "<meta name=\"viewport\"" not in html_content:
        warnings.append("Missing viewport meta tag (mobile responsiveness)")

    if "<meta charset=" not in html_content:
        warnings.append("Missing charset declaration")

    if "<title>" not in html_content:
        warnings.append("Missing page title")

    # Display results
    if errors:
        print(f"\n❌ {len(errors)} Validation Error(s):")
        for error in errors:
            print(f"  - {error}")
    else:
        print("\n✓ No validation errors found")

    if warnings:
        print(f"\n⚠️  {len(warnings)} Warning(s):")
        for warning in warnings:
            print(f"  - {warning}")

    return {"errors": errors, "warnings": warnings, "valid": len(errors) == 0}


def test_full_workflow():
    """
    Test the complete workflow with mock data.
    """
    print("\n" + "=" * 80)
    print("🧪 FULL WORKFLOW TEST (With Mock Data)")
    print("=" * 80)

    # Create mock state
    state = mock_test_workflow()

    # Validate structure
    validation = validate_html_structure(state["html_content"])

    # Save to file
    print("\n" + "-" * 80)
    print("Saving HTML to file")
    print("-" * 80)

    output_path = "output.html"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(state["html_content"])

    print(f"\n✓ HTML file saved to: {output_path}")
    print(f"  File size: {len(state['html_content'])} bytes")
    print(f"  Framework: {state['framework_choice']}")
    print(f"  Valid: {validation['valid']}")

    # Display summary
    print("\n" + "=" * 80)
    print("✅ TEST COMPLETED")
    print("=" * 80)
    print(f"\nGenerated file: output.html")
    print("You can now open this file in a web browser to see the result.")

    return state, validation


def test_with_real_api(user_prompt: str):
    """
    Test with real API (requires OPENAI_API_KEY).
    """
    import os

    if not os.getenv("OPENAI_API_KEY"):
        print("\n⚠️  OPENAI_API_KEY not set. Cannot run real API test.")
        print("Set OPENAI_API_KEY environment variable to use real LLM.")
        return

    print("\n" + "=" * 80)
    print("🧪 RUNNING WITH REAL API")
    print("=" * 80)

    try:
        from html_generation_agent import run_html_generation_workflow

        run_html_generation_workflow(user_prompt)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise


if __name__ == "__main__":
    # Run mock test by default
    state, validation = test_full_workflow()

    # Optionally run with real API
    # Uncomment below and set OPENAI_API_KEY to test with real LLM
    # test_with_real_api("Create a modern landing page for a tech startup")

    print(
        "\n\n💡 Next Steps:"
    )
    print("1. Open 'output.html' in your web browser")
    print("2. Set OPENAI_API_KEY environment variable to test with real LLM")
    print("3. Run: python html_generation_agent.py")
