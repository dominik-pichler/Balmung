import sqlite3

# Connect to the SQLite database (this will create the database if it doesn't exist)
conn = sqlite3.connect('/../data/mydatabase.db')

# Create a cursor object to execute SQL queries
cursor = conn.cursor()

# Create a table
cursor.execute('''CREATE TABLE IF NOT EXISTS terminal2 (
                    id INTEGER PRIMARY KEY,
                    name TEXT,
                    age INTEGER)''')

# Insert some data into the table
users_data = [
    ('Alice', 30),
    ('Bob', 25),
    ('Charlie', 35),
    ('Alice', 30),
    ('Bob', 25),
    ('Charlie', 35)
]


cursor.executemany('''INSERT INTO terminal (name, age) VALUES (?, ?)''', users_data)

# Commit the changes
conn.commit()

# Execute the SQL query to get all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")

# Fetch all the results
tables = cursor.fetchall()

# Print the list of tables
print("Tables in the database:")
for table in tables:
    print(table[0])

# Close the cursor and the connection
cursor.close()
conn.close()

