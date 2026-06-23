import json
import os
from database import init_db, SessionLocal, Project, Allocation, TeamMember, Task

def seed():
    print("Initializing DB schemas...")
    init_db()
    
    db = SessionLocal()
    
    DATA_PATH = os.path.join(os.path.dirname(__file__), "p", "portal_full_db_snapshot.json")
    print(f"Loading data from {DATA_PATH}...")
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    tables = data.get("tables", {})
    
    print("Clearing existing data...")
    db.query(Project).delete()
    db.query(Allocation).delete()
    db.query(TeamMember).delete()
    db.query(Task).delete()
    db.commit()

    print("Inserting projects...")
    projects_data = tables.get("projects", {}).get("rows", [])
    if projects_data:
        db.bulk_insert_mappings(Project, projects_data)
        
    print("Inserting allocations...")
    allocations_data = tables.get("allocations", {}).get("rows", [])
    if allocations_data:
        db.bulk_insert_mappings(Allocation, allocations_data)
        
    print("Inserting team members...")
    team_data = tables.get("team_members", {}).get("rows", [])
    if team_data:
        db.bulk_insert_mappings(TeamMember, team_data)
        
    print("Inserting tasks...")
    tasks_data = tables.get("tasks", {}).get("rows", [])
    if tasks_data:
        db.bulk_insert_mappings(Task, tasks_data)
        
    db.commit()
    db.close()
    print("Database seeded successfully!")

if __name__ == "__main__":
    seed()
