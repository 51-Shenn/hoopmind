#!/usr/bin/env bash
# Switch between LLM and NLU modes for HoopMind Rasa chatbot.
# Usage: ./switch_mode.sh [llm|nlu]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODE="${1:-}"

if [[ -z "$MODE" ]]; then
    if grep -q "CompactLLMCommandGenerator" "$SCRIPT_DIR/config.yml" 2>/dev/null; then
        echo "Current mode: llm"
    elif grep -q "DIETClassifier" "$SCRIPT_DIR/config.yml" 2>/dev/null; then
        echo "Current mode: nlu"
    else
        echo "Current mode: unknown"
    fi
    echo "Usage: $0 [llm|nlu]"
    exit 0
fi

case "$MODE" in
    llm)
        cp "$SCRIPT_DIR/config_llm.yml" "$SCRIPT_DIR/config.yml"
        echo "Switched to LLM mode (Gemini + Flows)"
        ;;
    nlu)
        cp "$SCRIPT_DIR/config_nlu.yml" "$SCRIPT_DIR/config.yml"
        echo "Switched to NLU mode (DIETClassifier + TEDPolicy)"
        ;;
    *)
        echo "Error: Unknown mode '$MODE'. Use 'llm' or 'nlu'."
        exit 1
        ;;
esac

echo "Run 'rasa train' to retrain with the new config."
