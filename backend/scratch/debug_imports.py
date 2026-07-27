import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

print("1. Importing backend.models...")
import backend.models

print("2. Importing backend.main...")
import backend.main

print("\nChecking keys in sys.modules matching models or database:")
for key in sorted(sys.modules.keys()):
    if "models" in key or "database" in key:
        print(f"  {key}: {sys.modules[key]}")

print("\n3. Checking metadata tables and their indexes:")
from backend.database import Base
for table_name, table in Base.metadata.tables.items():
    print(f"Table: {table_name}")
    print(f"  Indexes in python metadata: {[idx.name for idx in table.indexes]}")
