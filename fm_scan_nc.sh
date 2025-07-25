#!/bin/bash
# FM Radio Band Scan using netcat (nc) with HackRF UDP Server
# This demonstrates how to interact with the UDP server using standard tools

SERVER_HOST=${1:-localhost}
SERVER_PORT=${2:-5000}

echo "🎵 FM Radio Band Scan via UDP"
echo "Server: $SERVER_HOST:$SERVER_PORT"
echo "=================================="

# Function to send command and get response
send_udp_command() {
    local command="$1"
    local timeout=${2:-5}
    echo "$command" | nc -u -w $timeout "$SERVER_HOST" "$SERVER_PORT"
}

# Step 1: Connect to server
echo "📡 Connecting to server..."
response=$(send_udp_command "CONNECT")
echo "Response: $(echo "$response" | head -c 100)..."

# Step 2: Start FM radio scan
echo ""
echo "🎵 Starting FM radio band scan (88-108 MHz)..."
fm_command='START_STREAM {"args": ["-f", "88:108", "-g", "20", "-l", "16", "-w", "1000000"]}'
response=$(send_udp_command "$fm_command")
echo "Response: $response"

# Step 3: Listen to stream data for 10 seconds
echo ""
echo "📻 Listening to FM scan data for 10 seconds..."
echo "Sample data:"

# Use timeout to limit listening time
timeout 10s nc -u -l "$SERVER_PORT" > /tmp/fm_scan_data.txt &
NC_PID=$!

# Wait a bit for data collection
sleep 10

# Kill the listener if still running
kill $NC_PID 2>/dev/null

# Show sample of collected data
if [ -f /tmp/fm_scan_data.txt ]; then
    echo "📊 Data sample (first 10 lines):"
    head -10 /tmp/fm_scan_data.txt
    echo ""
    echo "📈 Total lines collected: $(wc -l < /tmp/fm_scan_data.txt)"
    
    # Show data rate
    file_size=$(stat -c%s /tmp/fm_scan_data.txt)
    echo "📏 Data size: $file_size bytes"
    echo "⚡ Estimated rate: $((file_size / 10)) bytes/second"
else
    echo "❌ No data collected - check if server is running"
fi

# Step 4: Stop the stream
echo ""
echo "⏹️ Stopping stream..."
response=$(send_udp_command "STOP_STREAM")
echo "Response: $response"

# Step 5: Disconnect
echo ""
echo "👋 Disconnecting..."
response=$(send_udp_command "DISCONNECT")
echo "Response: $response"

# Cleanup
rm -f /tmp/fm_scan_data.txt

echo ""
echo "✅ FM scan completed!"
