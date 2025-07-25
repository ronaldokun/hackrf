#!/usr/bin/env python3
"""
HackRF HTTP Wrapper
A simple HTTP server that proxies requests to the HackRF UDP server,
enabling curl and other HTTP clients to interact with the system.
"""

import asyncio
import json
import socket
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HackRFHTTPHandler(BaseHTTPRequestHandler):
    """HTTP handler that proxies requests to HackRF UDP server"""
    
    def __init__(self, *args, **kwargs):
        self.udp_host = kwargs.pop('udp_host', 'localhost')
        self.udp_port = kwargs.pop('udp_port', 5000)
        super().__init__(*args, **kwargs)
    
    def log_message(self, format, *args):
        """Override to use our logger"""
        logger.info(f"{self.address_string()} - {format % args}")
    
    def do_GET(self):
        """Handle GET requests"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        query_params = parse_qs(parsed_path.query)
        
        try:
            if path == '/':
                self._serve_help_page()
            elif path == '/connect':
                self._handle_connect()
            elif path == '/stats':
                self._handle_stats()
            elif path == '/ping':
                self._handle_ping()
            elif path == '/disconnect':
                self._handle_disconnect()
            elif path == '/scan/fm':
                self._handle_fm_scan(query_params)
            elif path == '/scan/custom':
                self._handle_custom_scan(query_params)
            else:
                self._send_error(404, "Endpoint not found")
                
        except Exception as e:
            logger.error(f"Error handling GET {path}: {e}")
            self._send_error(500, f"Server error: {str(e)}")
    
    def do_POST(self):
        """Handle POST requests"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            
            if path == '/start_stream':
                self._handle_start_stream(post_data)
            elif path == '/stop_stream':
                self._handle_stop_stream()
            else:
                self._send_error(404, "Endpoint not found")
                
        except Exception as e:
            logger.error(f"Error handling POST {path}: {e}")
            self._send_error(500, f"Server error: {str(e)}")
    
    def _send_udp_command(self, command, timeout=5):
        """Send command to UDP server and get response"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(timeout)
            
            sock.sendto(command.encode('utf-8'), (self.udp_host, self.udp_port))
            response, addr = sock.recvfrom(4096)
            
            sock.close()
            return response.decode('utf-8', errors='ignore')
            
        except Exception as e:
            raise Exception(f"UDP communication failed: {str(e)}")
    
    def _send_json_response(self, data, status=200):
        """Send JSON response"""
        response_data = json.dumps(data, indent=2)
        
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(response_data)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        self.wfile.write(response_data.encode('utf-8'))
    
    def _send_text_response(self, text, status=200):
        """Send plain text response"""
        self.send_response(status)
        self.send_header('Content-Type', 'text/plain')
        self.send_header('Content-Length', str(len(text)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        self.wfile.write(text.encode('utf-8'))
    
    def _send_error(self, status, message):
        """Send error response"""
        error_data = {"error": message, "status": status}
        self._send_json_response(error_data, status)
    
    def _serve_help_page(self):
        """Serve help/documentation page"""
        help_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>HackRF HTTP API</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                .endpoint { background: #f5f5f5; padding: 10px; margin: 10px 0; border-radius: 5px; }
                .method { color: #2196F3; font-weight: bold; }
                code { background: #e8e8e8; padding: 2px 5px; border-radius: 3px; }
            </style>
        </head>
        <body>
            <h1>🎵 HackRF HTTP API Wrapper</h1>
            <p>This HTTP API provides curl-friendly access to the HackRF UDP server.</p>
            
            <h2>📡 Endpoints</h2>
            
            <div class="endpoint">
                <span class="method">GET</span> <code>/connect</code> - Connect to HackRF server
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span> <code>/stats</code> - Get server statistics  
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span> <code>/ping</code> - Ping server
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span> <code>/scan/fm?duration=10</code> - FM radio band scan
                <br><small>Parameters: duration (seconds, default: 10)</small>
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span> <code>/scan/custom?freq=400:450&gain=20&duration=5</code> - Custom frequency scan
                <br><small>Parameters: freq (MHz range), gain, lna_gain, bin_width, duration</small>
            </div>
            
            <div class="endpoint">
                <span class="method">POST</span> <code>/start_stream</code> - Start custom stream
                <br><small>Body: JSON with "args" array</small>
            </div>
            
            <div class="endpoint">
                <span class="method">POST</span> <code>/stop_stream</code> - Stop current stream
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span> <code>/disconnect</code> - Disconnect from server
            </div>
            
            <h2>📋 curl Examples</h2>
            <pre>
# FM radio scan for 10 seconds
curl "http://localhost:8080/scan/fm?duration=10"

# Custom frequency scan
curl "http://localhost:8080/scan/custom?freq=400:450&gain=20&duration=5"

# Server stats
curl "http://localhost:8080/stats"

# Start custom stream
curl -X POST "http://localhost:8080/start_stream" \\
     -H "Content-Type: application/json" \\
     -d '{"args": ["-f", "88:108", "-g", "20", "-l", "16"]}'
            </pre>
        </body>
        </html>
        """
        
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.send_header('Content-Length', str(len(help_html)))
        self.end_headers()
        self.wfile.write(help_html.encode('utf-8'))
    
    def _handle_connect(self):
        """Handle connect request"""
        response = self._send_udp_command("CONNECT")
        try:
            data = json.loads(response)
            self._send_json_response(data)
        except json.JSONDecodeError:
            self._send_text_response(response)
    
    def _handle_stats(self):
        """Handle stats request"""
        response = self._send_udp_command("STATS")
        try:
            data = json.loads(response)
            self._send_json_response(data)
        except json.JSONDecodeError:
            self._send_text_response(response)
    
    def _handle_ping(self):
        """Handle ping request"""
        response = self._send_udp_command("PING")
        if response.strip() == "PONG":
            self._send_json_response({"status": "success", "response": "PONG"})
        else:
            self._send_text_response(response)
    
    def _handle_disconnect(self):
        """Handle disconnect request"""
        response = self._send_udp_command("DISCONNECT")
        if response.strip() == "DISCONNECTED":
            self._send_json_response({"status": "success", "message": "Disconnected"})
        else:
            self._send_text_response(response)
    
    def _handle_fm_scan(self, query_params):
        """Handle FM radio scan request"""
        duration = int(query_params.get('duration', [10])[0])
        
        # Use a dedicated UDP socket for this client session
        client_sock = None
        try:
            client_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            client_sock.settimeout(10.0)
            server_addr = (self.udp_host, self.udp_port)
            
            # Step 1: Connect to server
            logger.info("Connecting to HackRF UDP server...")
            client_sock.sendto(b"CONNECT", server_addr)
            response, addr = client_sock.recvfrom(4096)
            
            connect_response = response.decode('utf-8', errors='ignore')
            logger.info(f"Connect response: {connect_response[:100]}...")
            
            # Verify connection was successful
            try:
                connect_data = json.loads(connect_response)
                if connect_data.get('status') != 'connected':
                    self._send_json_response({"error": "Failed to connect to server", "details": connect_data})
                    return
            except json.JSONDecodeError:
                logger.warning("Non-JSON connect response, continuing...")
            
            # Step 2: Start FM scan
            logger.info("Starting FM radio scan...")
            fm_command = 'START_STREAM {"args": ["-f", "88:108", "-g", "20", "-l", "16", "-w", "1000000"]}'
            client_sock.sendto(fm_command.encode('utf-8'), server_addr)
            response, addr = client_sock.recvfrom(4096)
            
            start_response = response.decode('utf-8', errors='ignore')
            logger.info(f"Start stream response: {start_response}")
            
            try:
                start_data = json.loads(start_response)
                if start_data.get('status') != 'stream_started':
                    self._send_json_response({"error": "Failed to start stream", "details": start_data})
                    return
            except json.JSONDecodeError:
                self._send_error(500, f"Invalid response from server: {start_response}")
                return
            
            # Step 3: Collect streaming data
            logger.info(f"Collecting data for {duration} seconds...")
            collected_data = []
            client_sock.settimeout(2.0)  # Shorter timeout for data collection
            
            start_time = time.time()
            consecutive_timeouts = 0
            
            while time.time() - start_time < duration:
                try:
                    data, addr = client_sock.recvfrom(8192)
                    line = data.decode('utf-8', errors='ignore').strip()
                    
                    # Filter out JSON responses and keep only data lines
                    if line and not line.startswith('{') and ',' in line:
                        collected_data.append(line)
                        consecutive_timeouts = 0
                    
                except socket.timeout:
                    consecutive_timeouts += 1
                    # If no data for 10 seconds, something might be wrong
                    if consecutive_timeouts > 5:
                        logger.warning(f"No data received for {consecutive_timeouts * 2} seconds")
                        if consecutive_timeouts > 15:  # 30 seconds without data
                            break
                    continue
            
            logger.info(f"Collected {len(collected_data)} lines of data")
            
            # Step 4: Stop stream
            logger.info("Stopping stream...")
            client_sock.settimeout(10.0)
            client_sock.sendto(b"STOP_STREAM", server_addr)
            try:
                response, addr = client_sock.recvfrom(4096)
                logger.info(f"Stop response: {response.decode('utf-8', errors='ignore')}")
            except socket.timeout:
                logger.warning("No response to STOP_STREAM command")
            
            # Step 5: Disconnect
            logger.info("Disconnecting...")
            client_sock.sendto(b"DISCONNECT", server_addr)
            try:
                response, addr = client_sock.recvfrom(4096)
                logger.info(f"Disconnect response: {response.decode('utf-8', errors='ignore')}")
            except socket.timeout:
                logger.warning("No response to DISCONNECT command")
            
        except Exception as e:
            logger.error(f"Error during FM scan: {e}")
            self._send_error(500, f"Scan failed: {str(e)}")
            return
        finally:
            if client_sock:
                client_sock.close()
        
        # Return results
        result = {
            "scan_type": "FM Radio Band",
            "frequency_range": "88-108 MHz", 
            "duration_seconds": duration,
            "lines_collected": len(collected_data),
            "sample_data": collected_data[:10] if collected_data else [],
            "total_lines": len(collected_data),
            "data_rate_per_second": len(collected_data) / duration if duration > 0 else 0
        }
        
        self._send_json_response(result)
    
    def _handle_custom_scan(self, query_params):
        """Handle custom frequency scan request"""
        freq_range = query_params.get('freq', ['88:108'])[0]
        gain = query_params.get('gain', ['20'])[0]
        lna_gain = query_params.get('lna_gain', ['16'])[0]
        bin_width = query_params.get('bin_width', ['1000000'])[0]
        duration = int(query_params.get('duration', [10])[0])
        
        # Build command args
        args = ["-f", freq_range, "-g", gain, "-l", lna_gain, "-w", bin_width]
        
        # Use the same session management approach as FM scan
        client_sock = None
        try:
            client_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            client_sock.settimeout(10.0)
            server_addr = (self.udp_host, self.udp_port)
            
            # Step 1: Connect to server
            logger.info("Connecting to HackRF UDP server for custom scan...")
            client_sock.sendto(b"CONNECT", server_addr)
            response, addr = client_sock.recvfrom(4096)
            
            connect_response = response.decode('utf-8', errors='ignore')
            logger.info(f"Connect response: {connect_response[:100]}...")
            
            # Verify connection was successful
            try:
                connect_data = json.loads(connect_response)
                if connect_data.get('status') != 'connected':
                    self._send_json_response({"error": "Failed to connect to server", "details": connect_data})
                    return
            except json.JSONDecodeError:
                logger.warning("Non-JSON connect response, continuing...")
            
            # Step 2: Start custom scan
            logger.info(f"Starting custom scan: {args}")
            command = f'START_STREAM {{"args": {json.dumps(args)}}}'
            client_sock.sendto(command.encode('utf-8'), server_addr)
            response, addr = client_sock.recvfrom(4096)
            
            start_response = response.decode('utf-8', errors='ignore')
            logger.info(f"Start stream response: {start_response}")
            
            try:
                start_data = json.loads(start_response)
                if start_data.get('status') != 'stream_started':
                    self._send_json_response({"error": "Failed to start stream", "details": start_data})
                    return
            except json.JSONDecodeError:
                self._send_error(500, f"Invalid response from server: {start_response}")
                return
            
            # Step 3: Collect streaming data
            logger.info(f"Collecting data for {duration} seconds...")
            collected_data = []
            client_sock.settimeout(2.0)  # Shorter timeout for data collection
            
            start_time = time.time()
            consecutive_timeouts = 0
            
            while time.time() - start_time < duration:
                try:
                    data, addr = client_sock.recvfrom(8192)
                    line = data.decode('utf-8', errors='ignore').strip()
                    
                    # Filter out JSON responses and keep only data lines
                    if line and not line.startswith('{') and ',' in line:
                        collected_data.append(line)
                        consecutive_timeouts = 0
                    
                except socket.timeout:
                    consecutive_timeouts += 1
                    # If no data for 10 seconds, something might be wrong
                    if consecutive_timeouts > 5:
                        logger.warning(f"No data received for {consecutive_timeouts * 2} seconds")
                        if consecutive_timeouts > 15:  # 30 seconds without data
                            break
                    continue
            
            logger.info(f"Collected {len(collected_data)} lines of data")
            
            # Step 4: Stop stream
            logger.info("Stopping custom scan stream...")
            client_sock.settimeout(10.0)
            client_sock.sendto(b"STOP_STREAM", server_addr)
            try:
                response, addr = client_sock.recvfrom(4096)
                logger.info(f"Stop response: {response.decode('utf-8', errors='ignore')}")
            except socket.timeout:
                logger.warning("No response to STOP_STREAM command")
            
            # Step 5: Disconnect
            logger.info("Disconnecting...")
            client_sock.sendto(b"DISCONNECT", server_addr)
            try:
                response, addr = client_sock.recvfrom(4096)
                logger.info(f"Disconnect response: {response.decode('utf-8', errors='ignore')}")
            except socket.timeout:
                logger.warning("No response to DISCONNECT command")
            
        except Exception as e:
            logger.error(f"Error during custom scan: {e}")
            self._send_error(500, f"Scan failed: {str(e)}")
            return
        finally:
            if client_sock:
                client_sock.close()
        
        # Return results
        result = {
            "scan_type": "Custom Frequency Scan",
            "frequency_range": freq_range + " MHz",
            "parameters": {
                "vga_gain": gain,
                "lna_gain": lna_gain,
                "bin_width": bin_width
            },
            "duration_seconds": duration,
            "lines_collected": len(collected_data),
            "data": collected_data if collected_data else [],
            "total_lines": len(collected_data),
            "data_rate_per_second": len(collected_data) / duration if duration > 0 else 0
        }
        
        self._send_json_response(result)
    
    def _handle_start_stream(self, post_data):
        """Handle start stream POST request"""
        try:
            data = json.loads(post_data.decode('utf-8'))
            args = data.get('args', [])
            
            if not args:
                self._send_error(400, "Missing 'args' in request body")
                return
            
            # Connect and start stream
            self._send_udp_command("CONNECT")
            command = f'START_STREAM {{"args": {json.dumps(args)}}}'
            response = self._send_udp_command(command)
            
            try:
                response_data = json.loads(response)
                self._send_json_response(response_data)
            except json.JSONDecodeError:
                self._send_text_response(response)
                
        except json.JSONDecodeError:
            self._send_error(400, "Invalid JSON in request body")
    
    def _handle_stop_stream(self):
        """Handle stop stream request"""
        response = self._send_udp_command("STOP_STREAM")
        try:
            data = json.loads(response)
            self._send_json_response(data)
        except json.JSONDecodeError:
            self._send_text_response(response)


def create_handler_class(udp_host, udp_port):
    """Create handler class with UDP server configuration"""
    class ConfiguredHandler(HackRFHTTPHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, udp_host=udp_host, udp_port=udp_port, **kwargs)
    return ConfiguredHandler


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='HackRF HTTP Wrapper for curl compatibility')
    parser.add_argument('--http-host', default='localhost', help='HTTP server host')
    parser.add_argument('--http-port', type=int, default=8080, help='HTTP server port')
    parser.add_argument('--udp-host', default='localhost', help='HackRF UDP server host')
    parser.add_argument('--udp-port', type=int, default=5000, help='HackRF UDP server port')
    
    args = parser.parse_args()
    
    handler_class = create_handler_class(args.udp_host, args.udp_port)
    
    httpd = HTTPServer((args.http_host, args.http_port), handler_class)
    
    print(f"🌐 HackRF HTTP Wrapper started on http://{args.http_host}:{args.http_port}")
    print(f"📡 Proxying to HackRF UDP server at {args.udp_host}:{args.udp_port}")
    print(f"📖 Open http://{args.http_host}:{args.http_port} for API documentation")
    print("Press Ctrl+C to stop")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down HTTP wrapper...")
        httpd.shutdown()


if __name__ == '__main__':
    main()
