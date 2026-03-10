import pymysql

conn = pymysql.connect(host='localhost', user='root', password='Garima##120', db='financial_analytics')
cur = conn.cursor()
cur.execute('SHOW PROCESSLIST')
for row in cur.fetchall():
    print(row)
    if row[4] == 'Sleep':
        try:
            cur.execute(f"KILL {row[0]}")
            print(f"Killed {row[0]}")
        except:
            pass
conn.commit()

try:
    cur.execute("ALTER TABLE financial_statements ADD COLUMN filing_date VARCHAR(20)")
    print("Altered financial_statements")
except Exception as e:
    print(e)

try:
    cur.execute("ALTER TABLE financial_metrics ADD COLUMN filing_date VARCHAR(20)")
    print("Altered financial_metrics")
except Exception as e:
    print(e)
    
try:
    cur.execute("ALTER TABLE growth_metrics ADD COLUMN filing_date VARCHAR(20)")
    print("Altered growth_metrics")
except Exception as e:
    print(e)
    
try:
    cur.execute("ALTER TABLE acquisition_indicators ADD COLUMN filing_date VARCHAR(20)")
    print("Altered acquisition_indicators")
except Exception as e:
    print(e)
    
try:
    cur.execute("ALTER TABLE metadata ADD COLUMN filing_date VARCHAR(20)")
    print("Altered metadata")
except Exception as e:
    print(e)

conn.close()
