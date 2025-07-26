#!/usr/bin/env python3
"""
HackRF UDP Client Example
A simple client to demonstrate how to connect and stream from the HackRF UDP server.
"""

import socket
import json
import sys
import argparse
import time


class HackRFClient:
    """Simple UDP client for HackRF server"""

    def __init__(self, host="localhost", port=5000):
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.settimeout(10.0)  # 10 second timeout
        self.connected = False

    def connect(self):
        """Connect to the HackRF server"""
        try:
            print(f"Connecting to HackRF server at {self.host}:{self.port}...")
            self.socket.sendto(b"CONNECT", (self.host, self.port))

            response, addr = self.socket.recvfrom(4096)
            response_data = json.loads(response.decode("utf-8"))

            if response_data.get("status") == "connected":
                self.connected = True
                print("✓ Connected successfully!")
                print(f"Server version: {response_data['server_info']['version']}")
                print(f"Active clients: {response_data['server_info']['clients']}")
                return True
            else:
                print(f"✗ Connection failed: {response_data}")
                return False

        except Exception as e:
            print(f"✗ Connection error: {e}")
            return False

    def start_stream(self, hackrf_args):
        """Start a HackRF stream with specified arguments"""
        if not self.connected:
            print("✗ Not connected to server")
            return False

        try:
            command = {"args": hackrf_args}
            message = f"START_STREAM {json.dumps(command)}"

            print(f"Starting stream with args: {hackrf_args}")
            self.socket.sendto(message.encode("utf-8"), (self.host, self.port))

            response, addr = self.socket.recvfrom(4096)
            response_data = json.loads(response.decode("utf-8"))

            if response_data.get("status") == "stream_started":
                print("✓ Stream started successfully!")
                print(f"Processed args: {response_data.get('args', [])}")
                return True
            else:
                print(
                    f"✗ Stream start failed: {response_data.get('error', 'Unknown error')}"
                )
                return False

        except Exception as e:
            print(f"✗ Stream start error: {e}")
            return False

    def stop_stream(self):
        """Stop the current stream"""
        if not self.connected:
            print("✗ Not connected to server")
            return False

        try:
            print("Stopping stream...")
            self.socket.sendto(b"STOP_STREAM", (self.host, self.port))

            response, addr = self.socket.recvfrom(4096)
            response_data = json.loads(response.decode("utf-8"))

            if response_data.get("status") == "stream_stopped":
                print("✓ Stream stopped successfully!")
                return True
            else:
                print(f"✗ Stream stop failed: {response_data}")
                return False

        except Exception as e:
            print(f"✗ Stream stop error: {e}")
            return False

    def get_stats(self):
        """Get server statistics"""
        if not self.connected:
            print("✗ Not connected to server")
            return False

        try:
            self.socket.sendto(b"STATS", (self.host, self.port))
            response, addr = self.socket.recvfrom(4096)
            stats = json.loads(response.decode("utf-8"))

            print("\n📊 Server Statistics:")
            print(f"  Total clients: {stats['total_clients']}")
            print(f"  Server running: {stats['server_running']}")

            if stats["clients"]:
                print("  Active clients:")
                for client in stats["clients"]:
                    duration_mins = client["duration"] / 60
                    print(
                        f"    - {client['address']} (connected {duration_mins:.1f}m ago)"
                    )

            return True

        except Exception as e:
            print(f"✗ Stats error: {e}")
            return False

    def listen_to_stream(self, duration=None):
        """Listen to the HackRF data stream"""
        if not self.connected:
            print("✗ Not connected to server")
            return

        print(
            f"Listening to stream{'...' if duration is None else f' for {duration} seconds...'}"
        )
        print("Press Ctrl+C to stop listening")

        # Set socket to longer timeout for stream data
        self.socket.settimeout(5.0)

        start_time = time.time()
        line_count = 0
        last_data_time = time.time()
        consecutive_timeouts = 0

        try:
            while True:
                current_time = time.time()

                if duration and (current_time - start_time) > duration:
                    print(f"\n✓ Finished listening for {duration} seconds")
                    break

                try:
                    data, addr = self.socket.recvfrom(
                        65536
                    )  # Increased buffer size for radio spectrum stream

                    # Reset timeout counter on successful receive
                    consecutive_timeouts = 0
                    # last_data_time = current_time

                    # Handle different types of data
                    try:
                        # Try to decode as JSON first (server responses)
                        decoded = data.decode("utf-8")
                        # if decoded.startswith("{") or decoded.startswith("["):
                        #     try:
                        #         json_data = json.loads(decoded)
                        #         if "error" in json_data:
                        #             print(f"\n❌ Server error: {json_data['error']}")
                        #             break
                        #         elif "status" in json_data:
                        #             print(f"\n📢 Server message: {json_data}")
                        #             continue
                        #     except json.JSONDecodeError:
                        #         pass

                        # Regular hackrf_sweep output
                        line = decoded.strip()
                        if line and not line.startswith("{"):
                            line_count += 1
                            # Show full line
                            # Show first few lines in full, then sample
                            print(f"[{line_count:06d}] {line}")
                            # if line_count <= 10 or line_count % 100 == 0:
                            #    print(f"[{line_count:06d}] {line}")
                            # elif line_count % 1000 == 0:
                            #    elapsed = current_time - start_time
                            #    rate = line_count / elapsed if elapsed > 0 else 0
                            #    print(f"[{line_count:06d}] {line} (Rate: {rate:.1f} lines/sec)")

                    except UnicodeDecodeError:
                        # Handle binary data
                        line_count += 1
                        if line_count <= 5 or line_count % 1000 == 0:
                            print(f"[{line_count:06d}] Binary data: {len(data)} bytes")

                except socket.timeout:
                    consecutive_timeouts += 1

                    # Check if we've been without data for too long
                    if consecutive_timeouts > 20:  # 100 seconds without data
                        print(
                            f"\n⚠️ No data received for {consecutive_timeouts * 5} seconds"
                        )
                        print("Stream may have ended or connection lost")
                        break

                    # Periodic status update during timeouts
                    if consecutive_timeouts % 4 == 0:  # Every 20 seconds
                        elapsed = current_time - start_time
                        print(
                            f"\n📊 Status: {line_count} lines received in {elapsed:.1f}s (waiting for data...)"
                        )

                    continue

                except KeyboardInterrupt:
                    print("\n⏹️ Stopped listening by user")
                    break

        except Exception as e:
            print(f"\n✗ Stream listening error: {e}")
            import traceback

            print(f"Traceback: {traceback.format_exc()}")
        finally:
            # Restore original timeout
            self.socket.settimeout(10.0)
            elapsed = time.time() - start_time
            print(f"\n📈 Summary: Received {line_count} lines in {elapsed:.1f} seconds")

    def ping(self):
        """Send ping to server"""
        if not self.connected:
            print("✗ Not connected to server")
            return False

        try:
            self.socket.sendto(b"PING", (self.host, self.port))
            response, addr = self.socket.recvfrom(1024)

            if response == b"PONG":
                print("✓ Ping successful")
                return True
            else:
                print(f"✗ Unexpected ping response: {response}")
                return False

        except Exception as e:
            print(f"✗ Ping error: {e}")
            return False

    def disconnect(self):
        """Disconnect from server"""
        if self.connected:
            try:
                print("Disconnecting...")
                self.socket.sendto(b"DISCONNECT", (self.host, self.port))

                # Set a shorter timeout for disconnect response
                original_timeout = self.socket.gettimeout()
                self.socket.settimeout(2.0)

                # Try to get disconnect response, but handle data that might still be streaming
                disconnect_confirmed = False
                attempts = 0
                max_attempts = 5

                while not disconnect_confirmed and attempts < max_attempts:
                    try:
                        response, addr = self.socket.recvfrom(1024)
                        attempts += 1

                        if response == b"DISCONNECTED":
                            print("✓ Disconnected successfully")
                            disconnect_confirmed = True
                        else:
                            # Still receiving data, which is normal during disconnect
                            decoded = response.decode("utf-8", errors="ignore").strip()
                            if decoded.startswith("{") or "DISCONNECT" in decoded:
                                print("✓ Disconnected successfully")
                                disconnect_confirmed = True
                            else:
                                # This is just remaining stream data, ignore it
                                if attempts == 1:
                                    print(
                                        "⏳ Waiting for disconnect confirmation (still receiving data)..."
                                    )
                                continue

                    except socket.timeout:
                        # Timeout is fine, server might have already disconnected us
                        print("✓ Disconnected (timeout - assumed successful)")
                        break

                if not disconnect_confirmed and attempts >= max_attempts:
                    print(
                        "⚠️ Disconnect response unclear, but proceeding with disconnection"
                    )

                # Restore original timeout
                self.socket.settimeout(original_timeout)

            except Exception as e:
                print(f"Disconnect error: {e}")
            finally:
                self.connected = False

        self.socket.close()


def main():
    parser = argparse.ArgumentParser(
        description="HackRF UDP Client - Connect to HackRF UDP server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Connect and get stats
  python3 hackrf_udp_client.py --host localhost --port 5000 --stats
  
  # Start FM radio stream (88-108 MHz)
  python3 hackrf_udp_client.py --host localhost --start-stream -f 88:108 -g 20 -l 16 -w 1000000
  
  # Interactive mode
  python3 hackrf_udp_client.py --host localhost --interactive
        """,
    )

    parser.add_argument(
        "--host", default="localhost", help="Server host (default: localhost)"
    )
    parser.add_argument(
        "--port", type=int, default=5000, help="Server port (default: 5000)"
    )
    parser.add_argument("--stats", action="store_true", help="Get server statistics")
    parser.add_argument("--ping", action="store_true", help="Ping the server")
    parser.add_argument(
        "--start-stream", action="store_true", help="Start a stream with remaining args"
    )
    parser.add_argument(
        "--listen", type=int, metavar="SECONDS", help="Listen to stream for N seconds"
    )
    parser.add_argument("--interactive", action="store_true", help="Interactive mode")

    args, hackrf_args = parser.parse_known_args()

    client = HackRFClient(args.host, args.port)

    try:
        # Connect to server
        if not client.connect():
            sys.exit(1)

        if args.stats:
            client.get_stats()

        elif args.ping:
            client.ping()

        elif args.start_stream:
            if not hackrf_args:
                print("✗ No HackRF arguments provided for stream")
                print("Example: --start-stream -f 88:108 -g 20 -l 16 -w 1000000")
                sys.exit(1)

            if client.start_stream(hackrf_args):
                if args.listen:
                    client.listen_to_stream(args.listen)
                else:
                    print("Stream started. Use --listen to receive data.")

        elif args.interactive:
            print("\n🎛️  Interactive HackRF Client")
            print("Commands: stats, ping, start, stop, listen, quit")

            while True:
                try:
                    cmd = input("\nhackrf> ").strip().lower()

                    if cmd == "quit" or cmd == "exit":
                        break
                    elif cmd == "stats":
                        client.get_stats()
                    elif cmd == "ping":
                        client.ping()
                    elif cmd == "start":
                        args_input = input(
                            "HackRF args (e.g., -f 88:108 -g 20 -l 16): "
                        ).strip()
                        if args_input:
                            hackrf_args = args_input.split()
                            client.start_stream(hackrf_args)
                        else:
                            print("No arguments provided")
                    elif cmd == "stop":
                        client.stop_stream()
                    elif cmd == "listen":
                        duration_input = input(
                            "Duration in seconds (or press Enter for indefinite): "
                        ).strip()
                        duration = int(duration_input) if duration_input else None
                        client.listen_to_stream(duration)
                    elif cmd == "help":
                        print("Available commands:")
                        print("  stats  - Get server statistics")
                        print("  ping   - Ping the server")
                        print("  start  - Start a stream")
                        print("  stop   - Stop current stream")
                        print("  listen - Listen to stream data")
                        print("  quit   - Exit the client")
                    else:
                        print(
                            f"Unknown command: {cmd}. Type 'help' for available commands."
                        )

                except KeyboardInterrupt:
                    print("\nUse 'quit' to exit")
                except EOFError:
                    break

        else:
            # Just connect and show server info
            print("Connected. Use --help to see available options.")

    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        client.disconnect()


if __name__ == "__main__":
    main()
