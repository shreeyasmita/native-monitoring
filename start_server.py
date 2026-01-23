#!/usr/bin/env python3
"""
Production startup script for Cloud Native Monitor
"""

from app import app
import os

if __name__ == "__main__":
    # Production settings for faster response
    app.config.update(
        DEBUG=False,
        TESTING=False,
        PROPAGATE_EXCEPTIONS=False
    )
    
    print("=" * 60)
    print("Cloud Native System Monitor API Starting...")
    print("Production Mode - Optimized for Performance")
    print("=" * 60)
    print(f"Health Check:    http://localhost:5000/health")
    print(f"Prometheus:      http://localhost:5000/metrics")
    print(f"JSON (All):      http://localhost:5000/json")
    print(f"Dashboard:       http://localhost:5000/")
    print("=" * 60)
    
    # Use production WSGI server settings
    app.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 5000)),
        debug=False,  # Disable debug for faster response
        threaded=True,  # Enable threading for concurrent requests
        use_reloader=False  # Disable reloader for production
    )