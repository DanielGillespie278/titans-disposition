"""Minimal CLI for titans-disposition."""
import argparse
import sys


def main():
    parser = argparse.ArgumentParser(
        prog="titans",
        description="TITANS Disposition Engine — test-time memory substrate with adaptive gates",
    )
    sub = parser.add_subparsers(dest="command")

    # init command
    init_parser = sub.add_parser("init", help="Initialize disposition storage")
    init_parser.add_argument(
        "--claude-code", action="store_true",
        help="Register Claude Code hook (prints setup instructions)",
    )

    # deposit command
    deposit_parser = sub.add_parser("deposit", help="Deposit text into M-vector")
    deposit_parser.add_argument("text", help="Text to deposit")
    deposit_parser.add_argument(
        "--conversation", "-c", default="default",
        help="Conversation ID (default: 'default')",
    )

    # read command
    read_parser = sub.add_parser("read", help="Read current M-vector metrics")
    read_parser.add_argument(
        "--conversation", "-c", default="default",
        help="Conversation ID (default: 'default')",
    )

    # list command
    sub.add_parser("list", help="List all saved conversations")

    # reset command
    reset_parser = sub.add_parser("reset", help="Reset a conversation's state")
    reset_parser.add_argument(
        "--conversation", "-c", default="default",
        help="Conversation ID (default: 'default')",
    )

    args = parser.parse_args()

    if args.command == "init":
        from titans_disposition.storage import JSONBackedMemoryStore
        store = JSONBackedMemoryStore()
        print(f"Initialized storage at {store.storage_dir}")
        if getattr(args, "claude_code", False):
            print(
                "Claude Code hook registration:\n"
                "  Copy .claude/hooks/titans_disposition.py to ~/.claude/hooks/"
            )

    elif args.command == "deposit":
        from titans_disposition.engine import DispositionEngine
        engine = DispositionEngine(conversation_id=args.conversation)
        result = engine.deposit(args.text)
        print(f"Domain:    {result['domain']}")
        print(f"Correction: {result['correction']}")
        print(f"Surprise:  {result['surprise']:.4f}")
        print(f"M norm:    {result['m_norm']:.4f}")
        print(f"Updates:   {result['update_count']}")
        print(f"Gates:     alpha={result['gates']['alpha']:.4f} "
              f"theta={result['gates']['theta']:.4f} "
              f"eta={result['gates']['eta']:.4f}")

    elif args.command == "read":
        from titans_disposition.engine import DispositionEngine
        engine = DispositionEngine(conversation_id=args.conversation)
        metrics = engine.read()
        print(f"Conversation: {metrics['conversation_id']}")
        print(f"M norm:       {metrics['m_norm']:.4f}")
        print(f"Updates:      {metrics['update_count']}")
        print(f"Crystallization: {metrics['total_crystallization']:.4f}")
        if metrics.get("v2_metrics"):
            v2 = metrics["v2_metrics"]
            print(f"V2 gates:     alpha={v2['gate_alpha_mean']:.4f} "
                  f"theta={v2['gate_theta_mean']:.4f} "
                  f"eta={v2['gate_eta_mean']:.4f}")
            print(f"V2 loss:      {v2['associative_loss_mean']:.4f}")

    elif args.command == "list":
        from titans_disposition.storage import JSONBackedMemoryStore
        store = JSONBackedMemoryStore()
        conversations = store.list_conversations()
        if conversations:
            print(f"Saved conversations ({len(conversations)}):")
            for conv_id in sorted(conversations):
                print(f"  - {conv_id}")
        else:
            print("No saved conversations.")

    elif args.command == "reset":
        from titans_disposition.engine import DispositionEngine
        engine = DispositionEngine(conversation_id=args.conversation)
        engine.reset()
        print(f"Reset conversation: {args.conversation}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
