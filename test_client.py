#!/usr/bin/env python3
"""
Simple test client for debugging HackRF UDP server connection issues
"""

import socket
import json
import time
import sys

def test_client():
    """Test the basic client connection and stream"""
    
    # Create UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(10.0)
    
    server_addr = ('localhost', 5000)
    
    try:
        print("🔗 Testing connection...")
        
        # Connect
        sock.sendto(b"CONNECT", server_addr)
        response, addr = sock.recvfrom(4096)
        print(f"✓ Connect response: {response.decode('utf-8')[:200]}...")
        
        # Start stream with basic FM radio args
        print("\n🎵 Starting FM radio stream...")
        command = {
            "args": ["-f", "88:108", "-g", "20", "-l", "16", "-w", "1000000"]
        }
        message = f"START_STREAM {json.dumps(command)}"
        
        sock.sendto(message.encode('utf-8'), server_addr)
        response, addr = sock.recvfrom(4096)
        
        response_data = json.loads(response.decode('utf-8'))
        if response_data.get('status') == 'stream_started':
            print("✓ Stream started successfully!")
            print(f"Args: {response_data.get('args', [])}")
            
            # Listen for data for 15 seconds
            print("\n📡 Listening for data for 15 seconds...")
            sock.settimeout(2.0)
            
            start_time = time.time()
            line_count = 0
            
            while time.time() - start_time < 15:
                try:
                    data, addr = sock.recvfrom(8192)
                    line_count += 1
                    
                    if line_count <= 5:
                        decoded = data.decode('utf-8', errors='ignore').strip()
                        print(f"[{line_count:03d}] {decoded[:100]}...")
                    elif line_count % 100 == 0:
                        print(f"[{line_count:03d}] Received {line_count} lines so far...")
                        
                except socket.timeout:
                    print(".", end="", flush=True)
                    continue
                    
            print(f"\n📊 Total lines received: {line_count}")
            
            # Stop stream
            print("\n⏹️ Stopping stream...")
            sock.settimeout(10.0)
            sock.sendto(b"STOP_STREAM", server_addr)
            response, addr = sock.recvfrom(4096)
            print(f"Stop response: {response.decode('utf-8')}")
            
        else:
            print(f"✗ Stream start failed: {response_data}")
            return False
            
        # Disconnect
        print("\n👋 Disconnecting...")
        sock.sendto(b"DISCONNECT", server_addr)
        response, addr = sock.recvfrom(1024)
        print(f"Disconnect response: {response}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False
        
    finally:
        sock.close()

if __name__ == '__main__':
    print("🧪 HackRF UDP Server Test Client")
    print("=" * 40)
    
    success = test_client()
    
    print("\n" + "=" * 40)
    if success:
        print("✅ Test completed successfully!")
    else:
        print("❌ Test failed!")
        sys.exit(1)
