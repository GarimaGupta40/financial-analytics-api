import sys
import os

from database import SessionLocal
import trend_analysis

def run():
    db = SessionLocal()
    res = trend_analysis.analyze_company_trends(db, "AAPL")
    print(res)
    db.close()

if __name__ == "__main__":
    run()
