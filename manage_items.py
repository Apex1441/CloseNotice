import sys
import os

# Add src to path so we can import from src
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.utils.persistence import add_item, remove_item, load_monitored_items

def print_help():
    print("Usage:")
    print("  python manage_items.py list")
    print("  python manage_items.py add fund <TICKER>")
    print("  python manage_items.py add stock <TICKER>")
    print("  python manage_items.py remove <TICKER>")

def main():
    if len(sys.argv) < 2:
        print_help()
        return

    command = sys.argv[1].lower()

    if command == "list":
        items = load_monitored_items()
        print("Currently monitored items:")
        print("Funds:")
        for f in items['funds']:
            print(f" - {f}")
        print("Stocks:")
        for s in items['stocks']:
            print(f" - {s}")

    elif command == "add":
        if len(sys.argv) < 4:
            print("Error: Usage: python manage_items.py add <fund|stock|item> <TICKER>")
            return
        
        type_str = sys.argv[2].lower()
        ticker = sys.argv[3].upper()
        
        is_fund = type_str == "fund"
        # If user just says 'add item AAPL', we can try to guess or default to stock
        if type_str not in ["fund", "stock"]:
             print(f"Ambiguous type '{type_str}', assuming 'stock' for {ticker}")
             is_fund = False
             
        items = add_item(ticker, is_fund=is_fund)
        print(f"Added {ticker} as {'fund' if is_fund else 'stock'}.")

    elif command == "remove":
        if len(sys.argv) < 3:
            print("Error: Missing ticker symbol")
            return
        ticker = sys.argv[2].upper()
        items = remove_item(ticker)
        print(f"Removed {ticker} from monitoring.")

    else:
        print_help()

if __name__ == "__main__":
    main()
