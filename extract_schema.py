from sqlalchemy import create_engine, inspect
import sys

engine = create_engine('mysql+pymysql://root:Garima##120@localhost/financial_analytics')
inspector = inspect(engine)

try:
    with open('db_schema.txt', 'w') as f:
        tables = ['financial_statements', 'financial_metrics', 'growth_metrics', 'acquisition_indicators', 'metadata']
        for t in tables:
            f.write(t + '\n')
            cols = getattr(inspector, 'get_columns')(t)
            for c in cols:
                f.write(f"  {c['name']} ({c['type']})\n")
except Exception as e:
    import traceback
    traceback.print_exc()

print("Schema extraction complete.")
