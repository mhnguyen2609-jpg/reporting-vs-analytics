import pandas as pd
import sys
import io

# Fix encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Read file without header to see raw data
file_path = sys.argv[1]
df = pd.read_excel(file_path, header=None)
print("First 10 rows (raw, no header):")
print(df.head(10).to_string())
