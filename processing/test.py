import sqlite3
import pandas as pd

# Step 1: Create a SQLite database (or connect to it if it exists)
db_name = 'example.db'
conn = sqlite3.connect(db_name)

# Step 2: Load the CSV file into a pandas DataFrame
csv_file_path = 'O:\VCT\processed\game_changers_2024_gamedata.csv'  # Change this to your CSV file path
df = pd.read_csv(csv_file_path)

# Step 3: Write the DataFrame to a SQLite table
# If the table doesn't exist, it will be created
table_name = 'game_data'
df.to_sql(table_name, conn, if_exists='replace', index=False)


# Step 5: Close the connection
conn.close()
