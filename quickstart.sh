#!/bin/bash
# Zen Stream — Quick Start
# Usage:
#   bash quickstart.sh              # 10s test
#   bash quickstart.sh zen          # 1h zen meditation
#   bash quickstart.sh sleep        # 8h sleep
#   bash quickstart.sh loop zen     # generate forever
#   bash quickstart.sh batch        # batch from presets.json

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "╔══════════════════════════════════════════════════════════╗"
echo "║              ZEN STREAM — Quick Start                   ║"
echo "╚══════════════════════════════════════════════════════════╝"

# Check Python
if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 not found"
    exit 1
fi

# Check ffmpeg
if command -v ffmpeg &>/dev/null; then
    echo "✓ ffmpeg found: $(ffmpeg -version 2>&1 | head -1 | cut -d' ' -f3)"
else
    echo "⚠ ffmpeg not found — will generate frames + audio separately"
    echo "  Install with: sudo apt install ffmpeg"
fi

echo ""

case "${1:-test}" in
    test)
        echo "Running 10s test..."
        python3 zen_stream.py -d 10 -r 240p -t julia -p zen -m meditation -i 40
        ;;
    zen)
        echo "Generating 1h zen meditation (720p)..."
        python3 zen_stream.py --preset zen
        ;;
    sleep)
        echo "Generating 8h sleep video (480p)..."
        python3 zen_stream.py --preset sleep
        ;;
    focus)
        echo "Generating 2h focus video (720p)..."
        python3 zen_stream.py --preset focus
        ;;
    aurora)
        echo "Generating 1h aurora video (1080p)..."
        python3 zen_stream.py --preset aurora
        ;;
    nature)
        echo "Generating 1h nature video (720p)..."
        python3 zen_stream.py --preset nature
        ;;
    batch)
        if [ ! -f "presets.json" ]; then
            echo "Generating sample presets.json..."
            python3 zen_stream.py --sample-config
        fi
        echo "Running batch from presets.json..."
        python3 zen_stream.py --batch presets.json
        ;;
    loop)
        PRESET="${2:-zen}"
        echo "Starting infinite loop with preset '$PRESET'..."
        echo "Press Ctrl+C to stop"
        python3 zen_stream.py --loop --preset "$PRESET"
        ;;
    upload)
        PRESET="${2:-zen}"
        echo "Generating + uploading with preset '$PRESET'..."
        python3 zen_stream.py --preset "$PRESET" --upload
        ;;
    *)
        echo "Usage: bash quickstart.sh [command]"
        echo ""
        echo "Commands:"
        echo "  test              10s test video"
        echo "  zen               1h zen meditation (720p)"
        echo "  sleep             8h sleep video (480p)"
        echo "  focus             2h focus video (720p)"
        echo "  aurora            1h aurora video (1080p)"
        echo "  nature            1h nature video (720p)"
        echo "  batch             Batch from presets.json"
        echo "  loop [preset]     Generate forever"
        echo "  upload [preset]   Generate + upload to YouTube"
        ;;
esac

echo ""
echo "Done! Check output/ directory."
