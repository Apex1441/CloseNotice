import pandas as pd
from pathlib import Path
from datetime import datetime

csv_path = Path(r'c:\Users\rocks\Documents\claude work space\CloseNotice\data\sentiment_history.csv')

if csv_path.exists():
    df = pd.read_csv(csv_path)
    
    # Convert timestamp to datetime and extract date
    df['timestamp_dt'] = pd.to_datetime(df['timestamp'])
    df['date'] = df['timestamp_dt'].dt.date
    
    # Sort by timestamp to ensure the latest is last
    df = df.sort_values('timestamp_dt')
    
    # Drop duplicates, keeping the last (most recent) entry for each ticker and date
    df_clean = df.drop_duplicates(subset=['ticker', 'date'], keep='last')
    
    # Remove helper columns
    df_clean = df_clean.drop(columns=['timestamp_dt', 'date'])
    
    # Save back
    df_clean.to_csv(csv_path, index=False)
    print(f"Deduplication complete. Removed {len(df) - len(df_clean)} duplicates.")
else:
    print("CSV file not found.")
