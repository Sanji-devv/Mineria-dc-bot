import csv
import io
import urllib.request

SHEET_URL = "https://docs.google.com/spreadsheets/d/1qKwtaT_9FOnwiCk5BtCKFJSslYUFdspL0R03AMM34vI/export?format=csv&gid=1512160994"

def check_sheet():
    print(f"Fetching {SHEET_URL}...")
    try:
        with urllib.request.urlopen(SHEET_URL) as response:
            content = response.read().decode('utf-8')
    except Exception as e:
        print(f"Error fetching: {e}")
        return

    reader = csv.reader(io.StringIO(content))
    rows = list(reader)
    print(f"Total rows: {len(rows)}")
    
    if len(rows) > 1:
        print("Header:", rows[0])
        print("First row:", rows[1])

    query = "weapon focus"
    found_count = 0
    
    print("\nSearching for 'weapon focus'...")
    for i, row in enumerate(rows[1:]):
        if len(row) < 2: continue
        char_name = row[1]
        
        # Check col 6+
        if len(row) > 6:
            for cell in row[6:]:
                val = cell.strip().lower()
                if query in val:
                    print(f"Match Row {i+2}: Name='{char_name}' Feat='{cell}' Val='{val}'")
                    found_count += 1

    print(f"Total matches found: {found_count}")

if __name__ == "__main__":
    check_sheet()
