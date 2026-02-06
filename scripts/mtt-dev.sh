#!/bin/bash
# MTT Development Environment - tmux workspace setup
#
# Usage:
#   ./scripts/mtt-dev.sh          # Split view: all 4 panes visible (default)
#   ./scripts/mtt-dev.sh --tabs   # Tab view: 4 separate windows
#
# Layout (split view):
#   ┌──────────────────┬──────────────────┐
#   │  dev (servers)   │  claude (main)   │
#   │  make dev        │  claude session  │
#   ├──────────────────┼──────────────────┤
#   │  claude2         │  shell           │
#   │  parallel work   │  git, tests      │
#   └──────────────────┴──────────────────┘
#
# Navigation:
#   Ctrl+B arrow  - move between panes
#   Ctrl+B z      - zoom into current pane (fullscreen toggle)
#   Ctrl+B q      - show pane numbers

SESSION="mtt"
PROJECT_DIR="$HOME/XLOG/terminal-pro/mtt-combined"
MODE="${1:---split}"

# If session already exists, just attach to it
if tmux has-session -t "$SESSION" 2>/dev/null; then
    echo "Session '$SESSION' already exists. Attaching..."
    tmux attach -t "$SESSION"
    exit 0
fi

if [ "$MODE" = "--tabs" ]; then
    # ═══════════════════════════════════════════
    # TAB MODE: 4 separate windows (switch with Ctrl+B 0-3)
    # ═══════════════════════════════════════════

    tmux new-session -d -s "$SESSION" -n "dev" -c "$PROJECT_DIR"
    tmux send-keys -t "$SESSION:dev" "make dev" Enter

    tmux new-window -t "$SESSION" -n "claude" -c "$PROJECT_DIR"
    tmux send-keys -t "$SESSION:claude" "claude" Enter

    tmux new-window -t "$SESSION" -n "claude2" -c "$PROJECT_DIR"

    tmux new-window -t "$SESSION" -n "shell" -c "$PROJECT_DIR"

    tmux select-window -t "$SESSION:claude"

else
    # ═══════════════════════════════════════════
    # SPLIT MODE: 2x2 grid, all visible at once
    # ═══════════════════════════════════════════

    # Create session with first pane (top-left: dev servers)
    tmux new-session -d -s "$SESSION" -n "dashboard" -c "$PROJECT_DIR"

    # Split right → top-right: main Claude
    tmux split-window -h -t "$SESSION:dashboard" -c "$PROJECT_DIR"

    # Split bottom on the left pane → bottom-left: claude2
    tmux select-pane -t "$SESSION:dashboard.0"
    tmux split-window -v -t "$SESSION:dashboard" -c "$PROJECT_DIR"

    # Split bottom on the right pane → bottom-right: shell
    tmux select-pane -t "$SESSION:dashboard.1"
    tmux split-window -v -t "$SESSION:dashboard" -c "$PROJECT_DIR"

    # Now we have 4 panes:
    #   0: top-left      1: top-right
    #   2: bottom-left   3: bottom-right

    # Start dev servers in top-left (pane 0)
    tmux send-keys -t "$SESSION:dashboard.0" "make dev" Enter

    # Start Claude in top-right (pane 1)
    tmux send-keys -t "$SESSION:dashboard.1" "claude" Enter

    # Bottom-left ready for second Claude (pane 2)
    tmux send-keys -t "$SESSION:dashboard.2" "# Claude 2: run 'claude' when ready" ""

    # Bottom-right is free shell (pane 3)
    tmux send-keys -t "$SESSION:dashboard.3" "# Shell: git, pytest, make test" ""

    # Focus on the main Claude pane (top-right)
    tmux select-pane -t "$SESSION:dashboard.1"
fi

tmux attach -t "$SESSION"
