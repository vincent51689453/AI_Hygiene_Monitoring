import sqlite3

#Setup/Connect to a Database HA_Hygiene
SQL_Database = sqlite3.connect('/home/nvidiatx2-001/Vincent-Dev/001-QE_Hand_Hygiene/path_analyzer/SQL_Database/HA_Hygiene.db')
print("[INFO] Accesed Database successfully")

#Setup Cursor
SQL_Cursor = SQL_Database.cursor()
output = SQL_Cursor.execute("SELECT systime,staffID,valid,invalid,totalContact,totalValid,totalInvalid from STAFF_HYGIENE")
for row in output:
        print("SysTime->",row[0],"ID =",row[1]," Valid =",row[2]," Invalid =",row[3],"Total-Contact=",row[4],"Total-Valid=",row[5],"Total-Invalid=",row[6])
        print("--------------------------------------------------------------------------------------------------------------")
        
print("\n")
print("[INFO] Record displayed successfully")
SQL_Database.commit()
SQL_Database.close()

