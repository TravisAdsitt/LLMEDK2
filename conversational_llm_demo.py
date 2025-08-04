"""
Conversational LLM Demo - Shows LLM autonomously researching EDK2 questions
"""
import os
import sys
import time
from pathlib import Path

# Add the current directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent))

from edk2_navigator.interactive_llm_session import create_interactive_session


def demonstrate_conversational_research():
    """Demonstrate LLM autonomously researching complex EDK2 questions"""
    print("🤖 Conversational EDK2 Research Assistant")
    print("=" * 60)
    print("Ask complex questions and watch the LLM research the answers!")
    print()
    
    # Configuration
    workspace_dir = "."
    edk2_path = "edk2"
    
    try:
        # Create session with OpenAI
        print("🔧 Initializing research assistant...")
        session = create_interactive_session(
            workspace_dir=workspace_dir,
            edk2_path=edk2_path,
            provider_name="openai",
            model="gpt-4-turbo-preview"
        )
        
        print(f"✅ Assistant ready with {len(session.mcp_server.tools)} research tools")
        print()
        
        # Example research questions that require autonomous investigation
        research_questions = [
            {
                "question": "Help me understand how the firmware initializes memory in OVMF",
                "description": "Complex question requiring DSC parsing, module analysis, and function tracing"
            },
            {
                "question": "What are the main entry points and boot sequence in the OVMF platform?",
                "description": "Requires finding entry functions, analyzing dependencies, and tracing call paths"
            },
            {
                "question": "How does OVMF handle PCI device initialization and what modules are involved?",
                "description": "Needs module searching, dependency analysis, and function investigation"
            },
            {
                "question": "Show me the security features implemented in OVMF and where they're located",
                "description": "Requires code searching, module analysis, and function examination"
            }
        ]
        
        for i, item in enumerate(research_questions, 1):
            print(f"{'='*80}")
            print(f"🔍 Research Question {i}: {item['question']}")
            print(f"📋 Expected Research: {item['description']}")
            print(f"{'='*80}")
            print()
            
            print(f"👤 User: {item['question']}")
            print()
            print("🤖 Assistant is researching... (this may take a moment)")
            print()
            
            try:
                # Send the question and let the LLM research autonomously
                response = session.send_message(item['question'])
                
                # Show what the LLM discovered
                print("📊 Research Summary:")
                print(f"   • Research time: {response['total_time']:.1f} seconds")
                print(f"   • Tools used: {response['context']['total_tool_calls']} tool calls")
                print(f"   • Information gathered: {response['context']['total_messages']} exchanges")
                
                # Show the final answer
                if session.messages and session.messages[-1].role == "assistant":
                    final_answer = session.messages[-1].content
                    if final_answer and len(final_answer) > 50:
                        print()
                        print("🎯 Research Results:")
                        print("-" * 40)
                        # Show first part of the answer
                        lines = final_answer.split('\n')
                        for line in lines[:10]:  # Show first 10 lines
                            print(f"   {line}")
                        if len(lines) > 10:
                            print(f"   ... ({len(lines) - 10} more lines)")
                        print("-" * 40)
                
                # Show what tools were used in the research
                tool_usage = {}
                for msg in session.messages:
                    if msg.role == "tool" and msg.metadata:
                        tool_name = msg.metadata.get("tool_name")
                        if tool_name:
                            tool_usage[tool_name] = tool_usage.get(tool_name, 0) + 1
                
                if tool_usage:
                    print()
                    print("🔧 Research Tools Used:")
                    for tool, count in sorted(tool_usage.items(), key=lambda x: x[1], reverse=True):
                        print(f"   • {tool}: {count} times")
                
                print()
                input("Press Enter to continue to next question...")
                print()
                
            except Exception as e:
                print(f"❌ Research failed: {e}")
                continue
        
        print(f"{'='*80}")
        print("✅ Research demonstration completed!")
        print()
        print("💡 Key Capabilities Demonstrated:")
        print("   • Autonomous tool selection and usage")
        print("   • Multi-step research workflows")
        print("   • Context-aware investigation")
        print("   • Comprehensive answer synthesis")
        print()
        print(f"📁 Session saved as: {session.session_id}")
        print(f"📊 Total research exchanges: {session.context.total_messages}")
        print(f"🔧 Total tool calls made: {session.context.total_tool_calls}")
        
        return session
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def interactive_research_session(provider_name="openai", model=None):
    """Interactive session for asking research questions"""
    print("💬 Interactive EDK2 Research Session")
    print("=" * 50)
    print("Ask me anything about EDK2/OVMF and I'll research the answer!")
    print()
    print("Example questions:")
    print("• How does memory initialization work in OVMF?")
    print("• What's the boot sequence for UEFI applications?")
    print("• How are PCI devices enumerated?")
    print("• Where is the security validation code?")
    print("• How do drivers get loaded and initialized?")
    print()
    print("Commands: 'quit', 'help', 'summary', 'tools'")
    print()
    
    workspace_dir = "."
    edk2_path = "edk2"
    
    try:
        # Create research assistant
        session = create_interactive_session(
            workspace_dir=workspace_dir,
            edk2_path=edk2_path,
            provider_name=provider_name,
            model=model
        )
        
        print(f"🤖 Research Assistant ready! (Session: {session.session_id})")
        print(f"🔧 Available research tools: {len(session.mcp_server.tools)}")
        print()
        
        while True:
            try:
                user_input = input("🔍 Your question: ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("👋 Research session ended!")
                    break
                
                if user_input.lower() == 'help':
                    print("\n📋 Research Assistant Commands:")
                    print("   • Ask any question about EDK2/OVMF")
                    print("   • 'summary' - Show research session summary")
                    print("   • 'tools' - List available research tools")
                    print("   • 'quit' - End the session")
                    print("\n💡 Tips for better research:")
                    print("   • Be specific about what you want to understand")
                    print("   • Ask about processes, not just individual functions")
                    print("   • I can trace through complex workflows for you")
                    continue
                
                if user_input.lower() == 'summary':
                    summary = session.get_session_summary()
                    print(f"\n📊 Research Session Summary:")
                    print(f"   • Session ID: {summary['session_id']}")
                    print(f"   • Questions researched: {summary['messages_count'] // 2}")  # Rough estimate
                    print(f"   • Total tool calls: {summary['context']['total_tool_calls']}")
                    print(f"   • Files analyzed: {len(summary['context']['active_files'])}")
                    if summary['context']['current_dsc_context']:
                        print(f"   • Current build context: {summary['context']['current_dsc_context']}")
                    continue
                
                if user_input.lower() == 'tools':
                    print(f"\n🔧 Available Research Tools ({len(session.mcp_server.tools)}):")
                    print("   Navigation & Analysis:")
                    nav_tools = ['parse_dsc', 'get_included_modules', 'find_function', 'get_module_dependencies', 
                                'trace_call_path', 'analyze_function', 'search_code', 'get_build_statistics']
                    for tool in nav_tools:
                        print(f"     • {tool}")
                    
                    print("   Source Code Research:")
                    edit_tools = ['read_source_file', 'search_in_source_file', 'find_and_edit_function']
                    for tool in edit_tools:
                        print(f"     • {tool}")
                    continue
                
                if not user_input:
                    continue
                
                # Research the question
                print(f"\n🤖 Researching your question...")
                print("   (I'll use multiple tools to find comprehensive answers)")
                print()
                
                start_time = time.time()
                response = session.send_message(user_input)
                research_time = time.time() - start_time
                
                # Show the research results
                if session.messages and session.messages[-1].role == "assistant":
                    final_answer = session.messages[-1].content
                    if final_answer:
                        print("🎯 Research Results:")
                        print("-" * 60)
                        print(final_answer)
                        print("-" * 60)
                
                # Show research metrics
                print(f"\n📊 Research completed in {research_time:.1f}s")
                print(f"   • Tool calls made: {response['context']['total_tool_calls']}")
                print(f"   • Information exchanges: {response['context']['total_messages']}")
                
                print()
                
            except KeyboardInterrupt:
                print("\n👋 Research session ended!")
                break
            except Exception as e:
                print(f"❌ Research error: {e}")
                print("Please try rephrasing your question.")
    
    except Exception as e:
        print(f"❌ Failed to initialize research assistant: {e}")


def main():
    """Main demo function"""
    import argparse
    import time
    
    parser = argparse.ArgumentParser(description="Conversational EDK2 Research Assistant")
    parser.add_argument("--mode", choices=["demo", "interactive"], 
                       default="interactive", help="Demo mode to run")
    parser.add_argument("--provider", choices=["openai", "anthropic"], 
                       default="openai", help="LLM provider to use")
    
    args = parser.parse_args()
    model = None
    # Check for API keys
    if args.provider == "openai" and not os.getenv("OPENAI_API_KEY"):
        print("⚠️  Warning: OPENAI_API_KEY not set.")
        print("   Set your API key: export OPENAI_API_KEY='your-key-here'")
        print("   The demo will use mock responses without a real API key.")
        print()
        model = "gpt-3.5-turbo"
    
    if args.provider == "anthropic" and not os.getenv("ANTHROPIC_API_KEY"):
        print("⚠️  Warning: ANTHROPIC_API_KEY not set.")
        print("   Set your API key: export ANTHROPIC_API_KEY='your-key-here'")
        print("   The demo will use mock responses without a real API key.")
        print()
    if args.provider == "anthropic":
        model = "claude-sonnet-4-20250514"
    if args.provider == "openai":
        model = "gpt-4-turbo-preview"
    
    if args.mode == "demo":
        demonstrate_conversational_research()
    elif args.mode == "interactive":
        interactive_research_session(args.provider, model=model)


if __name__ == "__main__":
    main()
