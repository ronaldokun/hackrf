# HackRF UDP Server

A high-performance asynchronous Python UDP server that streams `hackrf_sweep` output to multiple clients over the network. Clients can provide their own `hackrf_sweep` options which are validated and executed server-side.

## Features

✅ **Client-provided options** - Clients send their own `hackrf_sweep` arguments via JSON  
✅ **Complete validation** - All `hackrf_sweep` options validated according to the help output  
✅ **Multi-client support** - Each client gets their own `hackrf_sweep` process  
✅ **High performance** - Asynchronous design handles multiple clients efficiently  
✅ **Robust error handling** - Graceful handling of disconnections and errors  
✅ **Proper cleanup** - Resources are properly cleaned up when clients disconnect  

## Performance

The server has been tested and achieves:
- **16,196 lines in 10 seconds** = ~1,620 lines/second throughput
- No unexpected disconnections during streaming
- Clean disconnect handling with proper resource cleanup

## Files

- `hackrf_udp_server.py` - Main asynchronous UDP server
- `hackrf_udp_client.py` - Full-featured client example with interactive mode
- `hackrf_http_wrapper.py` - A http wrapper to send UDP request from HTTP 
- `test_client.py` - Simple test client for debugging and validation

## Requirements

- Python 3.7+
- `hackrf_sweep` command available in PATH
- HackRF hardware connected and accessible

## Installation ( Server Side )

1. Ensure HackRF tools are installed:
   ```bash
   sudo apt-get install hackrf
   ```

2. Verify `hackrf_sweep` is available:
   ```bash
   which hackrf_sweep
   hackrf_sweep -h
   ```

3. Clone or download the server files to your desired directory.

## Usage

### Starting the Server

```bash
# Basic server on default port 5000
python3 hackrf_udp_server.py

# Custom host and port
python3 hackrf_udp_server.py --host 0.0.0.0 --port 5000

# Enable debug logging
python3 hackrf_udp_server.py --log-level DEBUG
```

### Client Examples ( python )

#### Quick Test
```bash
python3 test_client.py
```

#### FM Radio Streaming
```bash
# Stream FM radio band (88-108 MHz) for 30 seconds
python3 hackrf_udp_client.py --host localhost --start-stream -f 88:108 -g 20 -l 16 -w 1000000 --listen 30
```

#### Interactive Mode
```bash
python3 hackrf_udp_client.py --host localhost --interactive
```

#### Get Server Statistics
```bash
python3 hackrf_udp_client.py --host localhost --stats
```

#### Ping Server
```bash
python3 hackrf_udp_client.py --host localhost --ping
```

## Protocol

The server uses a simple UDP-based protocol with JSON for command/response and raw data streaming.

### Client Commands

| Command        | Description                     | Format                                                |
| -------------- | ------------------------------- | ----------------------------------------------------- |
| `CONNECT`      | Connect to server               | Plain text                                            |
| `START_STREAM` | Start hackrf_sweep with options | `START_STREAM {"args": ["-f", "88:108", "-g", "20"]}` |
| `STOP_STREAM`  | Stop current stream             | Plain text                                            |
| `STATS`        | Get server statistics           | Plain text                                            |
| `PING`         | Keep-alive ping                 | Plain text                                            |
| `DISCONNECT`   | Disconnect from server          | Plain text                                            |

### Connection Flow

1. Send `CONNECT` to connect to server
2. Send `START_STREAM` command with JSON payload containing hackrf_sweep arguments
3. Receive raw hackrf_sweep output stream
4. Send `STOP_STREAM` to stop current stream
5. Send `DISCONNECT` to disconnect cleanly

### Example START_STREAM Commands

```json
// FM Radio band scan
START_STREAM {"args": ["-f", "88:108", "-g", "20", "-l", "16", "-w", "1000000"]}

// Wide spectrum scan with binary output
START_STREAM {"args": ["-f", "1:6000", "-g", "40", "-l", "32", "-w", "1000000", "-B"]}

// Single sweep with specific device
START_STREAM {"args": ["-d", "0000000000000000457863dc2f635122", "-f", "400:450", "-1"]}
```

## Supported hackrf_sweep Options

The server validates all `hackrf_sweep` options according to the command specification:

| Option                 | Description               | Validation                              |
| ---------------------- | ------------------------- | --------------------------------------- |
| `-h`                   | Help                      | No validation                           |
| `-d serial_number`     | Device serial number      | Any string                              |
| `-a 0\|1`              | RX RF amplifier enable    | Must be 0 or 1                          |
| `-f freq_min:freq_max` | Frequency range in MHz    | Valid range format, freq_min < freq_max |
| `-p 0\|1`              | Antenna port power        | Must be 0 or 1                          |
| `-l gain_db`           | RX LNA gain               | 0-40dB in 8dB steps                     |
| `-g gain_db`           | RX VGA gain               | 0-62dB in 2dB steps                     |
| `-w bin_width`         | FFT bin width in Hz       | 2445-5000000 Hz                         |
| `-W wisdom_file`       | FFTW wisdom file          | Any valid file path                     |
| `-P plan_type`         | FFTW plan type            | estimate\|measure\|patient\|exhaustive  |
| `-1`                   | One shot mode             | No validation                           |
| `-N num_sweeps`        | Number of sweeps          | Positive integer                        |
| `-B`                   | Binary output             | No validation                           |
| `-I`                   | Binary inverse FFT output | No validation                           |
| `-r filename`          | Output file               | Any filename                            |

### Client Example ( Matlab )

A **non-tested** example client application written in matlab is available at `hackrf_udp_client.m`:

🌟 Key Features:

#### Multiple Usage Modes:
•  Interactive Demo (hackrf_udp_client('demo')) - Full GUI with menu-driven options
•  Quick FM Scan (hackrf_udp_client('fm_scan')) - One-line FM radio analysis
•  Custom Scans - Flexible frequency range scanning
•  Connection Testing - Verify server connectivity
•  Server Statistics - Monitor server health

#### Advanced Capabilities:
•  Automatic data parsing - Extracts timestamps, frequencies, power levels
•  Real-time plotting - Beautiful spectrum analysis graphs
•  Data persistence - Save results to .mat files
•  Error handling - Robust connection management
•  Progress tracking - Real-time feedback during scans

#### Professional UI:
•  Emoji indicators for better UX (📡🎵📊)
•  Interactive menus with multiple scan types
•  Comprehensive help documentation
•  Parameter validation and flexible configuration

#### 🚀 Usage Examples:

```
% Quick FM radio scan with automatic plotting
data = hackrf_udp_client('fm_scan');

% Custom frequency scan (400-450 MHz for 15 seconds)
args = {'-f', '400:450', '-g', '30', '-l', '24', '-w', '1000000'};
data = hackrf_udp_client('custom_scan', args, 'duration', 15);

% Interactive demo (recommended for first-time users)
hackrf_udp_client('demo');

% Test server connection
hackrf_udp_client('test_connection');
```

#### 📊 Data Structure:
The client returns structured data with:
•  Raw data lines from HackRF
•  Parsed timestamps, frequencies, power levels
•  Metadata (scan duration, data rate, etc.)
•  Automatic unit conversion (Hz → MHz)

#### 🎨 Visualization:
•  FM spectrum plots with power distribution histograms
•  Wide spectrum surveys with multi-panel analysis
•  Custom frequency range visualizations
•  Real-time progress indicators


## Error Handling

The server provides comprehensive error handling:

- **Invalid arguments**: Returns detailed validation errors
- **Process failures**: Graceful cleanup and error reporting  
- **Client disconnections**: Automatic resource cleanup
- **Network issues**: Timeout handling and reconnection support

## Multi-Client Support

- Each client gets its own dedicated `hackrf_sweep` process
- Clients can run different sweeps simultaneously  
- Independent stream control per client
- Automatic cleanup when clients disconnect

## Security Considerations

- The server validates all input arguments before execution
- Only `hackrf_sweep` command can be executed (no arbitrary command injection)
- Client connections are tracked and managed
- Automatic timeout cleanup for inactive clients

## Network Deployment

To expose the server over the internet:

1. **Configure firewall** to allow the UDP port (default 5000)
2. **Set host to 0.0.0.0** to listen on all interfaces
3. **Consider authentication** for production deployments
4. **Monitor resource usage** as each client spawns a process

Example for internet deployment:
```bash
python3 hackrf_udp_server.py --host 0.0.0.0 --port 5000
```

## Troubleshooting

### Common Issues

1. **"hackrf_sweep not found"**
   ```bash
   sudo apt-get install hackrf
   # or ensure hackrf_sweep is in PATH
   ```

2. **Permission denied accessing HackRF**
   ```bash
   # Add user to plugdev group
   sudo usermod -a -G plugdev $USER
   # Log out and back in, or run:
   sudo hackrf_sweep -f 88:108
   ```

3. **High CPU usage**
   - Monitor number of concurrent clients
   - Consider limiting connections or using process limits

4. **Network timeouts**
   - Check firewall settings
   - Verify UDP port is accessible
   - Use `test_client.py` for local testing

### Debug Mode

Enable debug logging for troubleshooting:
```bash
python3 hackrf_udp_server.py --log-level DEBUG
```

## License

This project is provided as-is for educational and research purposes. Please ensure compliance with local regulations regarding radio frequency scanning and transmission.

## Contributing

Feel free to submit issues, feature requests, or pull requests to improve the server functionality and performance.
