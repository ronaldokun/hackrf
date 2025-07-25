#!/usr/bin/env python3
"""
HackRF UDP Server
A high-performance asynchronous UDP server that streams hackrf_sweep output to multiple clients.
Clients can send their own hackrf_sweep options which are validated and executed.
"""

import asyncio
import argparse
import logging
import signal
import sys
import re
from typing import Set, Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from pathlib import Path
import json
import time


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ClientInfo:
    """Information about connected clients"""
    address: tuple
    last_seen: float
    connected_at: float
    hackrf_process: Optional[asyncio.subprocess.Process] = None
    active_stream: bool = False


class HackRFValidator:
    """Validates hackrf_sweep command line arguments based on the help output"""
    
    @staticmethod
    def validate_frequency_range(freq_str: str) -> bool:
        """Validate frequency range format (freq_min:freq_max)"""
        try:
            if ':' not in freq_str:
                return False
            freq_min, freq_max = freq_str.split(':')
            freq_min_val = float(freq_min)
            freq_max_val = float(freq_max)
            return freq_min_val < freq_max_val and freq_min_val > 0
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def validate_gain(gain_str: str, min_val: int, max_val: int, step: int) -> bool:
        """Validate gain values"""
        try:
            gain = int(gain_str)
            return min_val <= gain <= max_val and (gain - min_val) % step == 0
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def validate_bin_width(width_str: str) -> bool:
        """Validate FFT bin width (2445-5000000 Hz)"""
        try:
            width = int(width_str)
            return 2445 <= width <= 5000000
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def validate_num_sweeps(num_str: str) -> bool:
        """Validate number of sweeps"""
        try:
            num = int(num_str)
            return num > 0
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def validate_amp_antenna_enable(val_str: str) -> bool:
        """Validate amp/antenna enable (0 or 1)"""
        return val_str in ['0', '1']
    
    @staticmethod
    def validate_fftw_plan(plan_str: str) -> bool:
        """Validate FFTW plan type"""
        return plan_str in ['estimate', 'measure', 'patient', 'exhaustive']
    
    @classmethod
    def validate_hackrf_args(cls, args: List[str]) -> Tuple[bool, str, List[str]]:
        """Validate hackrf_sweep arguments and return (valid, error_msg, processed_args)"""
        if not args:
            return False, "No arguments provided", []
        
        processed_args = []
        i = 0
        
        while i < len(args):
            arg = args[i]
            
            # Help option
            if arg == '-h':
                processed_args.append(arg)
                i += 1
                continue
            
            # Serial number
            elif arg == '-d':
                if i + 1 >= len(args):
                    return False, f"Option {arg} requires a serial number", []
                processed_args.extend([arg, args[i + 1]])
                i += 2
            
            # RX RF amplifier (0 or 1)
            elif arg == '-a':
                if i + 1 >= len(args):
                    return False, f"Option {arg} requires a value (0 or 1)", []
                if not cls.validate_amp_antenna_enable(args[i + 1]):
                    return False, f"Invalid amp enable value: {args[i + 1]} (must be 0 or 1)", []
                processed_args.extend([arg, args[i + 1]])
                i += 2
            
            # Frequency range
            elif arg == '-f':
                if i + 1 >= len(args):
                    return False, f"Option {arg} requires frequency range (freq_min:freq_max)", []
                if not cls.validate_frequency_range(args[i + 1]):
                    return False, f"Invalid frequency range: {args[i + 1]} (format: freq_min:freq_max in MHz)", []
                processed_args.extend([arg, args[i + 1]])
                i += 2
            
            # Antenna port power (0 or 1)
            elif arg == '-p':
                if i + 1 >= len(args):
                    return False, f"Option {arg} requires a value (0 or 1)", []
                if not cls.validate_amp_antenna_enable(args[i + 1]):
                    return False, f"Invalid antenna enable value: {args[i + 1]} (must be 0 or 1)", []
                processed_args.extend([arg, args[i + 1]])
                i += 2
            
            # RX LNA gain (0-40dB, 8dB steps)
            elif arg == '-l':
                if i + 1 >= len(args):
                    return False, f"Option {arg} requires LNA gain value (0-40dB, 8dB steps)", []
                if not cls.validate_gain(args[i + 1], 0, 40, 8):
                    return False, f"Invalid LNA gain: {args[i + 1]} (0-40dB, 8dB steps)", []
                processed_args.extend([arg, args[i + 1]])
                i += 2
            
            # RX VGA gain (0-62dB, 2dB steps)
            elif arg == '-g':
                if i + 1 >= len(args):
                    return False, f"Option {arg} requires VGA gain value (0-62dB, 2dB steps)", []
                if not cls.validate_gain(args[i + 1], 0, 62, 2):
                    return False, f"Invalid VGA gain: {args[i + 1]} (0-62dB, 2dB steps)", []
                processed_args.extend([arg, args[i + 1]])
                i += 2
            
            # FFT bin width
            elif arg == '-w':
                if i + 1 >= len(args):
                    return False, f"Option {arg} requires bin width (2445-5000000 Hz)", []
                if not cls.validate_bin_width(args[i + 1]):
                    return False, f"Invalid bin width: {args[i + 1]} (2445-5000000 Hz)", []
                processed_args.extend([arg, args[i + 1]])
                i += 2
            
            # FFTW wisdom file
            elif arg == '-W':
                if i + 1 >= len(args):
                    return False, f"Option {arg} requires wisdom file path", []
                processed_args.extend([arg, args[i + 1]])
                i += 2
            
            # FFTW plan type
            elif arg == '-P':
                if i + 1 >= len(args):
                    return False, f"Option {arg} requires plan type", []
                if not cls.validate_fftw_plan(args[i + 1]):
                    return False, f"Invalid FFTW plan: {args[i + 1]} (estimate|measure|patient|exhaustive)", []
                processed_args.extend([arg, args[i + 1]])
                i += 2
            
            # One shot mode
            elif arg == '-1':
                processed_args.append(arg)
                i += 1
            
            # Number of sweeps
            elif arg == '-N':
                if i + 1 >= len(args):
                    return False, f"Option {arg} requires number of sweeps", []
                if not cls.validate_num_sweeps(args[i + 1]):
                    return False, f"Invalid number of sweeps: {args[i + 1]} (must be positive integer)", []
                processed_args.extend([arg, args[i + 1]])
                i += 2
            
            # Binary output
            elif arg == '-B':
                processed_args.append(arg)
                i += 1
            
            # Binary inverse FFT output
            elif arg == '-I':
                processed_args.append(arg)
                i += 1
            
            # Output file
            elif arg == '-r':
                if i + 1 >= len(args):
                    return False, f"Option {arg} requires output filename", []
                processed_args.extend([arg, args[i + 1]])
                i += 2
            
            else:
                return False, f"Unknown hackrf_sweep option: {arg}", []
        
        return True, "", processed_args


class HackRFSweepServer:
    """Asynchronous UDP server for HackRF sweep streaming"""
    
    def __init__(self, host: str = '0.0.0.0', port: int = 5000):
        self.host = host
        self.port = port
        self.clients: Dict[tuple, ClientInfo] = {}
        self.transport: Optional[asyncio.DatagramTransport] = None
        self.protocol: Optional['HackRFProtocol'] = None
        self.running = False
        self.client_timeout = 300  # 5 minutes client timeout
        self.stream_tasks: Dict[tuple, asyncio.Task] = {}  # Track streaming tasks per client
        
    async def start_server(self):
        """Start the UDP server"""
        logger.info(f"Starting HackRF UDP server on {self.host}:{self.port}")
        
        # Create UDP server
        loop = asyncio.get_running_loop()
        self.transport, self.protocol = await loop.create_datagram_endpoint(
            lambda: HackRFProtocol(self),
            local_addr=(self.host, self.port)
        )
        
        # Start background tasks
        self.running = True
        await asyncio.gather(
            self.cleanup_clients(),
            return_exceptions=True
        )
    
    async def start_hackrf_stream_for_client(self, client_address: tuple, hackrf_args: list):
        """Start a hackrf_sweep process for a specific client"""
        client_info = self.clients.get(client_address)
        if not client_info:
            return False, "Client not connected"
        
        # Stop existing stream if any
        await self.stop_hackrf_stream_for_client(client_address)
        
        cmd = ['hackrf_sweep'] + hackrf_args
        logger.info(f"Starting HackRF process for client {client_address}: {' '.join(cmd)}")
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            client_info.hackrf_process = process
            client_info.active_stream = True
            
            # Start streaming task for this client
            task = asyncio.create_task(
                self.stream_hackrf_output_to_client(client_address, process)
            )
            self.stream_tasks[client_address] = task
            
            logger.info(f"HackRF process started successfully for client {client_address}")
            return True, "Stream started successfully"
            
        except Exception as e:
            logger.error(f"Failed to start HackRF process for client {client_address}: {e}")
            return False, f"Failed to start stream: {str(e)}"
    
    async def stop_hackrf_stream_for_client(self, client_address: tuple):
        """Stop hackrf_sweep process for a specific client"""
        client_info = self.clients.get(client_address)
        if not client_info:
            return
        
        # Cancel streaming task
        if client_address in self.stream_tasks:
            task = self.stream_tasks[client_address]
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            del self.stream_tasks[client_address]
        
        # Stop process
        if client_info.hackrf_process and client_info.hackrf_process.returncode is None:
            client_info.hackrf_process.terminate()
            try:
                await asyncio.wait_for(client_info.hackrf_process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                client_info.hackrf_process.kill()
                await client_info.hackrf_process.wait()
        
        client_info.hackrf_process = None
        client_info.active_stream = False
        logger.info(f"Stopped HackRF stream for client {client_address}")
    
    async def stream_hackrf_output_to_client(self, client_address: tuple, process: asyncio.subprocess.Process):
        """Stream HackRF output to a specific client"""
        logger.info(f"Starting to stream HackRF output to client {client_address}")
        
        lines_sent = 0
        last_status_time = time.time()
        
        try:
            while self.running and process.returncode is None:
                # Read with timeout to avoid hanging
                try:
                    line = await asyncio.wait_for(process.stdout.readline(), timeout=1.0)
                except asyncio.TimeoutError:
                    # Check if client is still connected by updating last_seen
                    if client_address in self.clients:
                        current_time = time.time()
                        # Log status every 30 seconds
                        if current_time - last_status_time > 30:
                            logger.info(f"Client {client_address}: Still streaming, {lines_sent} lines sent")
                            last_status_time = current_time
                    continue
                
                if not line:
                    logger.info(f"HackRF process ended for client {client_address}")
                    break
                
                # Send to specific client
                try:
                    self.transport.sendto(line, client_address)
                    lines_sent += 1
                    
                    if client_address in self.clients:
                        self.clients[client_address].last_seen = time.time()
                        
                    # Log progress every 1000 lines
                    if lines_sent % 1000 == 0:
                        logger.debug(f"Sent {lines_sent} lines to client {client_address}")
                        
                except Exception as e:
                    logger.warning(f"Failed to send data to client {client_address}: {e}")
                    # Don't break immediately, client might reconnect
                    await asyncio.sleep(0.1)
                
        except asyncio.CancelledError:
            logger.info(f"HackRF output streaming cancelled for client {client_address} (sent {lines_sent} lines)")
        except Exception as e:
            logger.error(f"Error streaming HackRF output to client {client_address}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
        finally:
            logger.info(f"Finished streaming to client {client_address}, sent {lines_sent} lines total")
            # Clean up
            await self.stop_hackrf_stream_for_client(client_address)
    
    def add_client(self, address: tuple):
        """Add a new client"""
        if address not in self.clients:
            current_time = time.time()
            self.clients[address] = ClientInfo(
                address=address,
                last_seen=current_time,
                connected_at=current_time
            )
            logger.info(f"New client connected: {address}")
            logger.info(f"Total clients: {len(self.clients)}")
    
    def remove_client(self, address: tuple):
        """Remove a client"""
        if address in self.clients:
            del self.clients[address]
            logger.info(f"Client disconnected: {address}")
            logger.info(f"Total clients: {len(self.clients)}")
    
    async def cleanup_clients(self):
        """Periodically cleanup inactive clients"""
        while self.running:
            try:
                await asyncio.sleep(60)  # Check every minute
                current_time = time.time()
                inactive_clients = []
                
                for address, client_info in self.clients.items():
                    if current_time - client_info.last_seen > self.client_timeout:
                        inactive_clients.append(address)
                
                for address in inactive_clients:
                    self.remove_client(address)
                    logger.info(f"Removed inactive client: {address}")
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in client cleanup: {e}")
    
    async def stop_server(self):
        """Stop the server gracefully"""
        logger.info("Stopping HackRF UDP server...")
        self.running = False
        
        # Stop all client streams
        for client_address in list(self.clients.keys()):
            await self.stop_hackrf_stream_for_client(client_address)
        
        # Cancel all remaining stream tasks
        for task in self.stream_tasks.values():
            if not task.done():
                task.cancel()
        
        # Close transport
        if self.transport:
            self.transport.close()
        
        logger.info("Server stopped")
    
    def get_server_stats(self) -> dict:
        """Get server statistics"""
        current_time = time.time()
        
        # Count active hackrf processes
        active_processes = 0
        for client_info in self.clients.values():
            if client_info.hackrf_process and client_info.hackrf_process.returncode is None:
                active_processes += 1
        
        return {
            'total_clients': len(self.clients),
            'active_processes': active_processes,
            'clients': [
                {
                    'address': f"{client.address[0]}:{client.address[1]}",
                    'connected_at': client.connected_at,
                    'last_seen': client.last_seen,
                    'duration': current_time - client.connected_at,
                    'active_stream': client.active_stream
                }
                for client in self.clients.values()
            ],
            'server_running': self.running
        }


class HackRFProtocol(asyncio.DatagramProtocol):
    """UDP protocol handler for HackRF server"""
    
    def __init__(self, server: HackRFSweepServer):
        self.server = server
    
    def connection_made(self, transport):
        """Called when the protocol is created"""
        self.transport = transport
        logger.info("UDP server protocol created")
    
    def datagram_received(self, data, addr):
        """Handle incoming datagrams from clients"""
        try:
            message = data.decode('utf-8').strip()
            
            if message == "CONNECT":
                # Client wants to connect
                self.server.add_client(addr)
                response = json.dumps({
                    'status': 'connected',
                    'message': 'Successfully connected to HackRF server',
                    'server_info': {
                        'version': '2.0.0',
                        'clients': len(self.server.clients)
                    },
                    'usage': {
                        'commands': {
                            'CONNECT': 'Connect to the server',
                            'START_STREAM': 'Start hackrf_sweep with options (JSON format)',
                            'STOP_STREAM': 'Stop current stream',
                            'STATS': 'Get server statistics',
                            'PING': 'Keep-alive ping',
                            'DISCONNECT': 'Disconnect from server'
                        },
                        'start_stream_format': {
                            'command': 'START_STREAM',
                            'args': ['-f', '88:108', '-g', '20', '-l', '16']
                        }
                    }
                }).encode('utf-8')
                self.transport.sendto(response, addr)
                
            elif message.startswith("START_STREAM"):
                # Client wants to start a stream with hackrf_sweep options
                asyncio.create_task(self._handle_start_stream(message, addr))
                
            elif message == "STOP_STREAM":
                # Client wants to stop their stream
                asyncio.create_task(self._handle_stop_stream(addr))
                
            elif message == "STATS":
                # Client requests server statistics
                stats = self.server.get_server_stats()
                response = json.dumps(stats, indent=2).encode('utf-8')
                self.transport.sendto(response, addr)
                
            elif message == "PING":
                # Keep-alive ping from client
                if addr in self.server.clients:
                    self.server.clients[addr].last_seen = time.time()
                self.transport.sendto(b"PONG", addr)
                
            elif message == "DISCONNECT":
                # Client wants to disconnect
                asyncio.create_task(self._handle_disconnect(addr))
                
            else:
                # Unknown command
                error_response = json.dumps({
                    'error': 'Unknown command',
                    'valid_commands': ['CONNECT', 'START_STREAM', 'STOP_STREAM', 'STATS', 'PING', 'DISCONNECT'],
                    'example_start_stream': {
                        'command': 'START_STREAM',
                        'args': ['-f', '88:108', '-g', '20', '-l', '16', '-w', '1000000']
                    }
                }).encode('utf-8')
                self.transport.sendto(error_response, addr)
                
        except Exception as e:
            logger.error(f"Error handling datagram from {addr}: {e}")
            error_response = json.dumps({
                'error': f'Server error: {str(e)}'
            }).encode('utf-8')
            self.transport.sendto(error_response, addr)
    
    def error_received(self, exc):
        """Handle protocol errors"""
        logger.error(f"Protocol error: {exc}")
    
    def connection_lost(self, exc):
        """Called when the transport is closed"""
        if exc:
            logger.error(f"Connection lost: {exc}")
        else:
            logger.info("Connection closed normally")
    
    async def _handle_start_stream(self, message: str, addr: tuple):
        """Handle START_STREAM command"""
        try:
            # Parse JSON payload from message
            if message == "START_STREAM":
                # No arguments provided
                error_response = json.dumps({
                    'error': 'START_STREAM requires arguments',
                    'format': {
                        'command': 'START_STREAM',
                        'args': ['-f', '88:108', '-g', '20', '-l', '16']
                    }
                }).encode('utf-8')
                self.transport.sendto(error_response, addr)
                return
            
            # Extract JSON payload
            try:
                json_part = message[len("START_STREAM "):].strip()
                request = json.loads(json_part)
                hackrf_args = request.get('args', [])
            except (json.JSONDecodeError, KeyError) as e:
                error_response = json.dumps({
                    'error': f'Invalid JSON format: {str(e)}',
                    'format': {
                        'command': 'START_STREAM',
                        'args': ['-f', '88:108', '-g', '20', '-l', '16']
                    }
                }).encode('utf-8')
                self.transport.sendto(error_response, addr)
                return
            
            # Validate arguments
            is_valid, error_msg, processed_args = HackRFValidator.validate_hackrf_args(hackrf_args)
            
            if not is_valid:
                error_response = json.dumps({
                    'error': f'Invalid hackrf_sweep arguments: {error_msg}',
                    'provided_args': hackrf_args
                }).encode('utf-8')
                self.transport.sendto(error_response, addr)
                return
            
            # Start stream for client
            success, result_msg = await self.server.start_hackrf_stream_for_client(addr, processed_args)
            
            if success:
                response = json.dumps({
                    'status': 'stream_started',
                    'message': result_msg,
                    'args': processed_args
                }).encode('utf-8')
            else:
                response = json.dumps({
                    'error': result_msg,
                    'args': processed_args
                }).encode('utf-8')
            
            self.transport.sendto(response, addr)
            
        except Exception as e:
            logger.error(f"Error handling START_STREAM from {addr}: {e}")
            error_response = json.dumps({
                'error': f'Server error: {str(e)}'
            }).encode('utf-8')
            self.transport.sendto(error_response, addr)
    
    async def _handle_stop_stream(self, addr: tuple):
        """Handle STOP_STREAM command"""
        try:
            await self.server.stop_hackrf_stream_for_client(addr)
            response = json.dumps({
                'status': 'stream_stopped',
                'message': 'Stream stopped successfully'
            }).encode('utf-8')
            self.transport.sendto(response, addr)
            
        except Exception as e:
            logger.error(f"Error handling STOP_STREAM from {addr}: {e}")
            error_response = json.dumps({
                'error': f'Server error: {str(e)}'
            }).encode('utf-8')
            self.transport.sendto(error_response, addr)
    
    async def _handle_disconnect(self, addr: tuple):
        """Handle DISCONNECT command"""
        try:
            logger.info(f"Processing disconnect request from {addr}")
            
            # Stop any active stream first
            await self.server.stop_hackrf_stream_for_client(addr)
            
            # Small delay to ensure stream cleanup is complete
            await asyncio.sleep(0.1)
            
            # Remove client from active clients
            self.server.remove_client(addr)
            
            # Send disconnect confirmation
            self.transport.sendto(b"DISCONNECTED", addr)
            
            logger.info(f"Successfully disconnected client {addr}")
            
        except Exception as e:
            logger.error(f"Error handling DISCONNECT from {addr}: {e}")
            # Still try to send disconnect confirmation even if there was an error
            try:
                self.transport.sendto(b"DISCONNECTED", addr)
            except:
                pass


def validate_hackrf_args(args: list) -> list:
    """Validate and process hackrf_sweep arguments"""
    valid_args = []
    i = 0
    
    while i < len(args):
        arg = args[i]
        
        # Single character options that don't require values
        if arg in ['-h', '-1', '-B', '-I']:
            valid_args.append(arg)
            i += 1
            
        # Options that require a value
        elif arg in ['-d', '-a', '-f', '-p', '-l', '-g', '-w', '-W', '-P', '-N', '-r']:
            if i + 1 < len(args):
                valid_args.extend([arg, args[i + 1]])
                i += 2
            else:
                raise ValueError(f"Option {arg} requires a value")
        else:
            raise ValueError(f"Unknown hackrf_sweep option: {arg}")
    
    return valid_args


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='HackRF UDP Server - Stream hackrf_sweep output over UDP with client-provided options',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 hackrf_udp_server.py --port 5000
  python3 hackrf_udp_server.py --host 0.0.0.0 --port 5000

Client Protocol:
  1. Send "CONNECT" to connect to server
  2. Send START_STREAM command with JSON payload:
     START_STREAM {"args": ["-f", "88:108", "-g", "20", "-l", "16", "-w", "1000000"]}
  3. Receive hackrf_sweep output stream
  4. Send "STOP_STREAM" to stop current stream
  5. Send "DISCONNECT" to disconnect

Other Commands:
  STATS      - Get server statistics
  PING       - Keep-alive ping
        """
    )
    
    # Server options
    parser.add_argument('--host', default='0.0.0.0', 
                       help='Host IP to bind the server (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=5000,
                       help='Port to bind the server (default: 5000)')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       default='INFO', help='Logging level (default: INFO)')
    
    # Parse server arguments only
    args = parser.parse_args()
    
    # Configure logging level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    try:
        # Create and start server
        server = HackRFSweepServer(args.host, args.port)
        
        # Handle graceful shutdown
        def signal_handler():
            logger.info("Received shutdown signal")
            asyncio.create_task(server.stop_server())
        
        # Set up signal handlers
        loop = asyncio.get_running_loop()
        for sig in [signal.SIGTERM, signal.SIGINT]:
            loop.add_signal_handler(sig, signal_handler)
        
        # Start the server (no hackrf_args needed - clients provide them)
        await server.start_server()
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
