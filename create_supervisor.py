import sqlite3

conn = sqlite3.connect('sharmsetu.db')
c = conn.cursor()

username = input("Enter supervisor username: ")
password = input("Enter supervisor password: ")

# Check if exists
c.execute("SELECT * FROM supervisor WHERE username=?", (username,))
user = c.fetchone()

if user:
    print("Username already exists ❌ Try different username")
else:
    c.execute("INSERT INTO supervisor(username,password) VALUES(?,?)",(username,password))
    conn.commit()
    print("Supervisor created successfully ✔")

conn.close()