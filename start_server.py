#!/usr/bin/env python3
"""
Flame MCP Server Launcher
Checks environment and starts the MCP server with proper configuration.
"""

import os
import sys
from pathlib import Path

def check_environment():
    """Check if required environment variables are set."""
    required_vars = [
        "OPENAI_API_KEY",
        "OPENAI_API_BASE", 
        "QDRANT_HOST",
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\n💡 Please check your .env file and ensure all required variables are set.")
        print("   See env.example for reference.")
        return False
    
    return True

def check_dependencies():
    """Check if required dependencies are installed."""
    try:
        import fastmcp
        import qdrant_client
        import openai
        import dotenv
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("\n💡 Please install dependencies:")
        print("   pip install -r requirements.txt")
        return False

def main():
    """Main launcher function."""
    print("🚀 Flame MCP Server Launcher")
    print("=" * 40)
    
    # Check if .env file exists
    env_file = Path(".env")
    if not env_file.exists():
        print("⚠️  No .env file found. Creating from template...")
        if Path("env.example").exists():
            print("   Please copy env.example to .env and configure it:")
            print("   cp env.example .env")
        else:
            print("   Please create a .env file with your configuration.")
        sys.exit(1)
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    print("✅ Environment file loaded")
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    print("✅ Dependencies verified")
    
    # Check environment variables
    if not check_environment():
        sys.exit(1)
    
    print("✅ Environment configuration verified")
    
    # Check Qdrant connection
    print("🔍 Testing Qdrant connection...")
    try:
        from qdrant_client import QdrantClient
        client = QdrantClient(
            url=os.getenv("QDRANT_HOST"),
            port=os.getenv("QDRANT_PORT"),
        )
        
        # Try to get collection info
        collection_name = os.getenv("COLLECTION_NAME", "flame_docs")
        try:
            info = client.get_collection(collection_name)
            print(f"✅ Connected to Qdrant - Collection '{collection_name}' found")
            print(f"   Vectors: {info.vectors_count if hasattr(info, 'vectors_count') else 'unknown'}")
        except Exception:
            print(f"⚠️  Collection '{collection_name}' not found - you may need to run the processing pipeline first")
            
    except Exception as e:
        print(f"❌ Failed to connect to Qdrant: {e}")
        print("   Please ensure Qdrant is running and accessible")
        sys.exit(1)
    
    # Start the server
    print("\n🎯 Starting MCP Server...")
    print("   Server will run until interrupted (Ctrl+C)")
    print("   Logs will show search queries and results")
    print("-" * 40)
    
    try:
        from server import mcp
        mcp.run()
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped by user")
    except Exception as e:
        print(f"\n❌ Server error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 