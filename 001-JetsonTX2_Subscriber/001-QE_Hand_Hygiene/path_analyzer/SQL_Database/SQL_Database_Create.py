import sqlite3

#Setup/Connect to a Database HA_Hygiene
SQL_Database = sqlite3.connect('/home/nvidiatx2-001/Vincent-Dev/001-QE_Hand_Hygiene/path_analyzer/SQL_Database/HA_Hygiene.db')
print("[INFO] Accesed Database successfully")

#Setup Cursor
SQL_Cursor = SQL_Database.cursor()
SQL_Cursor.execute('''CREATE TABLE STAFF_HYGIENE (systime text,staffID int,valid int,invalid int,totalContact int,totalValid int, totalInvalid int)''')
print("[INFO] Table created successfully")
SQL_Database.commit()
SQL_Database.close()

