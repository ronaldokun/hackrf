#!/bin/bash
# HackRF curl Examples
# Demonstrates various ways to use curl with the HackRF HTTP wrapper

HTTP_SERVER=${1:-http://localhost:8080}

echo "🎵 HackRF curl Examples"
echo "Using HTTP server: $HTTP_SERVER"
echo "========================================"

echo ""
echo "📡 1. Check server connection"
curl -s "$HTTP_SERVER/ping" | jq '.'

echo ""
echo "📊 2. Get server statistics"
curl -s "$HTTP_SERVER/stats" | jq '.'

echo ""
echo "🎵 3. FM Radio Band Scan (10 seconds)"
echo "Command: curl \"$HTTP_SERVER/scan/fm?duration=10\""
curl -s "$HTTP_SERVER/scan/fm?duration=10" | jq '.'

echo ""
echo "📻 4. Custom frequency scan (400-450 MHz, 5 seconds)"
echo "Command: curl \"$HTTP_SERVER/scan/custom?freq=400:450&gain=30&lna_gain=24&duration=5\""
curl -s "$HTTP_SERVER/scan/custom?freq=400:450&gain=30&lna_gain=24&duration=5" | jq '.'

echo ""
echo "🎛️ 5. Start custom stream via POST"
echo "Command: curl -X POST with JSON payload"
curl -s -X POST "$HTTP_SERVER/start_stream" \
     -H "Content-Type: application/json" \
     -d '{"args": ["-f", "88:108", "-g", "20", "-l", "16", "-w", "1000000", "-1"]}' | jq '.'

echo ""
echo "⏹️ 6. Stop stream"
curl -s -X POST "$HTTP_SERVER/stop_stream" | jq '.'

echo ""
echo "✅ curl examples completed!"
echo ""
echo "🌐 More examples:"
echo "# Extended FM scan (30 seconds)"
echo "curl \"$HTTP_SERVER/scan/fm?duration=30\""
echo ""
echo "# Amateur radio 2m band (144-148 MHz)"
echo "curl \"$HTTP_SERVER/scan/custom?freq=144:148&gain=40&duration=15\""
echo ""
echo "# GSM band scan (890-960 MHz)"
echo "curl \"$HTTP_SERVER/scan/custom?freq=890:960&gain=35&lna_gain=32&duration=20\""
echo ""
echo "# Wide spectrum overview (100-1000 MHz, 60 seconds)"
echo "curl \"$HTTP_SERVER/scan/custom?freq=100:1000&gain=30&duration=60\""
