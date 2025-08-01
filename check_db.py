import sys
import os

# Add the 'src' directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from src.database import SessionLocal, Material

def check_and_fix_materials():
    db = SessionLocal()
    materials = db.query(Material).all()
    if not materials:
        print("No materials found in the database.")
    else:
        print(f"Found {len(materials)} materials:")
        for material in materials:
            print(f"  - ID: {material.id}, Title: {material.title}, Link: {material.link}")
            if material.id == 1:
                print("Found material with ID 1. Attempting to fix title...")
                material.title = "Test Material"
                db.commit()
                print("Material title updated successfully.")

    db.close()

if __name__ == "__main__":
    check_and_fix_materials()