"""
Interactive LLM Session Demo - Demonstrates the comprehensive LLM session management
"""
import os
import sys
from pathlib import Path

# Add the current directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent))

from edk2_navigator.interactive_llm_session import create_interactive_session


def demonstrate_basic_session():
    """Demonstrate basic interactive LLM session functionality"""
    print("🚀 Interactive LLM Session Demo")
    print("=" * 50)
    
    # Configuration
    workspace_dir = "."
    edk2_path = "edk2"
    
    print(f"📁 Workspace: {workspace_dir}")
    print(f"🔧 EDK2 Path: {edk2_path}")
    
    try:
        # Create session with OpenAI (you can also use "anthropic")
        print("\n🤖 Creating LLM session with OpenAI...")
        session = create_interactive_session(
            workspace_dir=workspace_dir,
            edk2_path=edk2_path,
            provider_name="openai",
            model="gpt-4-turbo-preview"
        )
        
        print(f"✅ Session created: {session.session_id}")
        print(f"📊 Available tools: {len(session.mcp_server.tools)}")
        
        # Demo conversation scenarios
        scenarios = [
            {
                "name": "Parse OVMF Platform",
                "message": "Please parse the OVMF X64 platform DSC file to understand the build context"
            },
            {
                "name": "Find UefiMain Function",
                "message": "Find the UefiMain function in the codebase and show me where it's defined"
            },
            {
                "name": "Analyze Module Dependencies",
                "message": "Show me the dependencies for the PlatformPei module"
            },
            {
                "name": "Edit Source File",
                "message": "Read the Platform.c file from OvmfPkg/PlatformPei and add a debug print statement"
            }
        ]
        
        for i, scenario in enumerate(scenarios, 1):
            print(f"\n{'='*60}")
            print(f"📋 Scenario {i}: {scenario['name']}")
            print(f"{'='*60}")
            
            # Send message and get response
            print(f"👤 User: {scenario['message']}")
            
            try:
                response = session.send_message(scenario['message'])
                
                print(f"\n📊 Session Statistics:")
                print(f"   • Total time: {response['total_time']:.2f}s")
                print(f"   • Total messages: {response['context']['total_messages']}")
                print(f"   • Total tool calls: {response['context']['total_tool_calls']}")
                
                # Show the final assistant response
                if session.messages and session.messages[-1].role == "assistant":
                    final_response = session.messages[-1].content
                    if final_response:
                        print(f"\n🤖 Assistant: {final_response[:200]}...")
                
                # Show session summary
                summary = session.get_session_summary()
                print(f"\n📈 Session Summary:")
                print(f"   • Messages in context: {summary['messages_count']}")
                print(f"   • Active files: {len(response['context']['active_files'])}")
                if response['context']['current_dsc_context']:
                    print(f"   • Current DSC: {response['context']['current_dsc_context']}")
                
            except Exception as e:
                print(f"❌ Error in scenario: {e}")
                continue
        
        # Export session for analysis
        print(f"\n{'='*60}")
        print("📤 Exporting Session")
        print(f"{'='*60}")
        
        export_path = session.export_session()
        print(f"✅ Session exported to: {export_path}")
        
        # Show session files
        summary = session.get_session_summary()
        print(f"\n📁 Session Files:")
        for file_type, file_path in summary['session_files'].items():
            if Path(file_path).exists():
                size = Path(file_path).stat().st_size
                print(f"   • {file_type}: {file_path} ({size} bytes)")
        
        print(f"\n✅ Demo completed successfully!")
        print(f"🔍 Session ID: {session.session_id}")
        
        return session
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def demonstrate_session_manager():
    """Demonstrate session management capabilities"""
    print("\n🗂️  Session Manager Demo")
    print("=" * 50)
    
    workspace_dir = "."
    edk2_path = "edk2"
    
    try:
        # Create session manager
        manager = SessionManager(workspace_dir, edk2_path)
        print(f"✅ Session manager initialized")
        
        # Create multiple sessions
        print(f"\n📝 Creating multiple sessions...")
        
        session1 = manager.create_session("openai", model="gpt-4-turbo-preview")
        print(f"   • Session 1: {session1.session_id}")
        
        # Simulate some activity
        session1.send_message("Parse the OVMF DSC file")
        
        session2 = manager.create_session("openai", model="gpt-3.5-turbo")
        print(f"   • Session 2: {session2.session_id}")
        
        # List all sessions
        print(f"\n📋 Listing all sessions:")
        sessions = manager.list_sessions()
        
        for session_info in sessions:
            print(f"   • {session_info['session_id']} ({session_info['status']})")
            print(f"     - Created: {session_info['created_at']}")
            print(f"     - Messages: {session_info['total_messages']}")
            print(f"     - Tool calls: {session_info['total_tool_calls']}")
        
        # Get specific session
        print(f"\n🔍 Retrieving specific session:")
        retrieved_session = manager.get_session(session1.session_id)
        if retrieved_session:
            print(f"   ✅ Retrieved session: {retrieved_session.session_id}")
            print(f"   📊 Messages: {len(retrieved_session.messages)}")
        
        print(f"\n✅ Session manager demo completed!")
        
        return manager
        
    except Exception as e:
        print(f"❌ Session manager demo failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def interactive_session_cli():
    """Interactive CLI for testing the LLM session"""
    print("\n💬 Interactive LLM Session CLI")
    print("=" * 50)
    print("Commands: 'quit', 'help', 'summary', 'export', 'tools'")
    
    workspace_dir = "."
    edk2_path = "edk2"
    
    try:
        # Create session
        session = create_interactive_session(
            workspace_dir=workspace_dir,
            edk2_path=edk2_path,
            provider_name="openai"  # Change to "anthropic" if preferred
        )
        
        print(f"✅ Session ready: {session.session_id}")
        print(f"🔧 Available tools: {len(session.mcp_server.tools)}")
        
        while True:
            try:
                user_input = input("\n👤 You: ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("👋 Goodbye!")
                    break
                
                if user_input.lower() == 'help':
                    print("\n📋 Available commands:")
                    print("   • quit/exit/q - Exit the session")
                    print("   • help - Show this help")
                    print("   • summary - Show session summary")
                    print("   • export - Export session data")
                    print("   • tools - List available tools")
                    print("   • Or just type your question/request")
                    continue
                
                if user_input.lower() == 'summary':
                    summary = session.get_session_summary()
                    print(f"\n📊 Session Summary:")
                    print(f"   • Session ID: {summary['session_id']}")
                    print(f"   • Messages: {summary['messages_count']}")
                    print(f"   • Tool calls: {summary['context']['total_tool_calls']}")
                    print(f"   • Active files: {len(summary['context']['active_files'])}")
                    if summary['context']['current_dsc_context']:
                        print(f"   • Current DSC: {summary['context']['current_dsc_context']}")
                    continue
                
                if user_input.lower() == 'export':
                    export_path = session.export_session()
                    print(f"✅ Session exported to: {export_path}")
                    continue
                
                if user_input.lower() == 'tools':
                    print(f"\n🔧 Available tools ({len(session.mcp_server.tools)}):")
                    for tool in session.mcp_server.tools:
                        print(f"   • {tool['name']}: {tool['description'][:60]}...")
                    continue
                
                if not user_input:
                    continue
                
                # Send message to LLM
                print(f"\n🤖 Processing...")
                response = session.send_message(user_input)
                
                # Show the response
                if session.messages and session.messages[-1].role == "assistant":
                    final_response = session.messages[-1].content
                    if final_response:
                        print(f"\n🤖 Assistant: {final_response}")
                
                # Show brief stats
                print(f"\n📊 Response time: {response['total_time']:.2f}s | "
                      f"Tool calls: {response['context']['total_tool_calls']} | "
                      f"Messages: {response['context']['total_messages']}")
                
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
    
    except Exception as e:
        print(f"❌ Failed to initialize interactive session: {e}")


def main():
    """Main demo function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Interactive LLM Session Demo")
    parser.add_argument("--mode", choices=["demo", "manager", "interactive"], 
                       default="demo", help="Demo mode to run")
    parser.add_argument("--provider", choices=["openai", "anthropic"], 
                       default="openai", help="LLM provider to use")
    
    args = parser.parse_args()
    
    # Check for API keys
    if args.provider == "openai" and not os.getenv("OPENAI_API_KEY"):
        print("⚠️  Warning: OPENAI_API_KEY not set. Using mock responses.")
        print("   Set your API key: export OPENAI_API_KEY='your-key-here'")
    
    if args.provider == "anthropic" and not os.getenv("ANTHROPIC_API_KEY"):
        print("⚠️  Warning: ANTHROPIC_API_KEY not set. Using mock responses.")
        print("   Set your API key: export ANTHROPIC_API_KEY='your-key-here'")
    
    if args.mode == "demo":
        demonstrate_basic_session()
    elif args.mode == "manager":
        demonstrate_session_manager()
    elif args.mode == "interactive":
        interactive_session_cli()


if __name__ == "__main__":
    main()
