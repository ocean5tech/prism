#!/usr/bin/env python3
"""
PostgreSQL Database Connection Test Script
Tests connection from various network interfaces
"""

import psycopg2
import socket
import sys
from datetime import datetime

# Database connection parameters
DB_PARAMS = {
    'database': 'prism_db',
    'user': 'prism_user',
    'password': 'prism_password',  # Update this with actual password
    'port': 5434
}

# Test different host addresses
TEST_HOSTS = [
    ('localhost', 'Local WSL connection'),
    ('127.0.0.1', 'WSL loopback'),
    ('172.20.51.134', 'WSL IP address'),
    ('0.0.0.0', 'All interfaces')
]

def test_network_connectivity(host, port):
    """Test if port is reachable"""
    try:
        sock = socket.create_connection((host, port), timeout=5)
        sock.close()
        return True
    except (socket.timeout, socket.error):
        return False

def test_db_connection(host):
    """Test PostgreSQL database connection"""
    try:
        conn_params = DB_PARAMS.copy()
        conn_params['host'] = host
        
        conn = psycopg2.connect(**conn_params)
        cursor = conn.cursor()
        
        # Test basic queries
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        
        cursor.execute("SELECT current_database();")
        database = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM information_schema.tables;")
        table_count = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        return {
            'success': True,
            'version': version.split('\n')[0],  # First line only
            'database': database,
            'table_count': table_count
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def main():
    print("PostgreSQL Connection Test")
    print("=" * 50)
    print(f"Test Time: {datetime.now()}")
    print(f"Testing Database: {DB_PARAMS['database']}")
    print(f"Testing User: {DB_PARAMS['user']}")
    print(f"Testing Port: {DB_PARAMS['port']}")
    print()
    
    for host, description in TEST_HOSTS:
        print(f"Testing {description} ({host}):")
        
        # Test network connectivity first
        if test_network_connectivity(host, DB_PARAMS['port']):
            print(f"  ✓ Network connectivity: OK")
            
            # Test database connection
            result = test_db_connection(host)
            if result['success']:
                print(f"  ✓ Database connection: OK")
                print(f"  ✓ PostgreSQL version: {result['version']}")
                print(f"  ✓ Connected to database: {result['database']}")
                print(f"  ✓ Tables found: {result['table_count']}")
                print("  → This connection should work from Windows!")
            else:
                print(f"  ✗ Database connection failed: {result['error']}")
        else:
            print(f"  ✗ Network connectivity: Failed")
            print("  → This host won't work from Windows")
        
        print()
    
    print("Windows Connection Instructions:")
    print("-" * 30)
    print("Use these connection parameters in your Windows PostgreSQL client:")
    print(f"Host: 172.20.51.134")
    print(f"Port: 5434")
    print(f"Database: prism_db")
    print(f"Username: prism_user")
    print(f"Password: [your_password]")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Test failed with error: {e}")
        sys.exit(1)