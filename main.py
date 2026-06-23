import json
import os
import sys
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

print("Starting Cockpit Backend...", file=sys.stderr)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"status": "ok", "message": "Cockpit backend is running"}

@app.get("/health")
def health():
    return {"status": "healthy"}

try:
    from database import SessionLocal, Project, Allocation, TeamMember, Task
    print("✓ Database module imported successfully", file=sys.stderr)
except Exception as e:
    print(f"✗ Failed to import database: {e}", file=sys.stderr)
    SessionLocal = None
    Project = None
    Allocation = None
    TeamMember = None
    Task = None

def load_data():
    if SessionLocal is None:
        print("⚠ Database not available, returning empty dataset", file=sys.stderr)
        return {
            "tables": {
                "projects": {"rows": []},
                "allocations": {"rows": []},
                "team_members": {"rows": []},
                "tasks": {"rows": []}
            }
        }
    
    try:
        db = SessionLocal()
    except Exception as e:
        print(f"✗ Could not create database session: {e}", file=sys.stderr)
        return {
            "tables": {
                "projects": {"rows": []},
                "allocations": {"rows": []},
                "team_members": {"rows": []},
                "tasks": {"rows": []}
            }
        }
    
    try:
        def to_dict(obj):
            return {k: v for k, v in obj.__dict__.items() if not k.startswith('_')}
            
        return {
            "tables": {
                "projects": {"rows": [to_dict(p) for p in db.query(Project).all()] if Project else []},
                "allocations": {"rows": [to_dict(a) for a in db.query(Allocation).all()] if Allocation else []},
                "team_members": {"rows": [to_dict(t) for t in db.query(TeamMember).all()] if TeamMember else []},
                "tasks": {"rows": [to_dict(t) for t in db.query(Task).all()] if Task else []}
            }
        }
    except Exception as e:
        print(f"✗ Error loading data: {e}", file=sys.stderr)
        return {
            "tables": {
                "projects": {"rows": []},
                "allocations": {"rows": []},
                "team_members": {"rows": []},
                "tasks": {"rows": []}
            }
        }
    finally:
        try:
            db.close()
        except:
            pass

@app.get("/api/dashboard")
def get_dashboard_data():
    db = load_data()
    tables = db.get("tables", {})
    
    raw_projects = tables.get("projects", {}).get("rows", [])
    raw_allocations = tables.get("allocations", {}).get("rows", [])
    raw_team = tables.get("team_members", {}).get("rows", [])
    raw_tasks = tables.get("tasks", {}).get("rows", [])
    
    all_clients = set()
    
    # Map project clients and statuses
    project_clients = {}
    project_statuses = {}
    for p in raw_projects:
        client = p.get("client", "adani")
        p_name = p["name"]
        project_clients[p_name] = client
        project_statuses[p_name] = p.get("status", "")
        all_clients.add(client)
    
    # Process Employees (Case-insensitive matching)
    employee_map = {}
    for member in raw_team:
        client = member.get("client", "adani")
        all_clients.add(client)
        emp_key = member["name"].lower().strip()
        if emp_key in employee_map:
            if client not in employee_map[emp_key]["clients"]:
                employee_map[emp_key]["clients"].append(client)
        else:
            employee_map[emp_key] = {
                "name": member["name"], 
                "role": member["designation"], 
                "projects_count": 0,
                "clients": [client],
                "_active_projects": set()
            }
        
    # Link allocations and tasks to employees
    project_allocations = {}
    
    def assign_employee_to_project(emp_name, proj_name):
        emp_name_lower = emp_name.lower().strip()
        if emp_name_lower in employee_map:
            emp = employee_map[emp_name_lower]
            # Track for employee's project count (only if not completed)
            if project_statuses.get(proj_name) != "Completed":
                emp["_active_projects"].add(proj_name)
                
            # Track cross-pollinating clients regardless of project completion status
            proj_client = project_clients.get(proj_name)
            if proj_client and proj_client not in emp["clients"]:
                emp["clients"].append(proj_client)
            
            # Track for project's assigned team
            if proj_name not in project_allocations:
                project_allocations[proj_name] = []
            
            current_assigned = [e["name"] for e in project_allocations[proj_name]]
            if emp["name"] not in current_assigned:
                clean_emp = {k: v for k, v in emp.items() if k != "_active_projects"}
                project_allocations[proj_name].append(clean_emp)

    for alloc in raw_allocations:
        assign_employee_to_project(alloc["member_name"], alloc["project_name"])
        
    for task in raw_tasks:
        if task.get("assigned_to"):
            assign_employee_to_project(task["assigned_to"], task["project_name"])
            
    # Process Blockers
    project_blockers = {}
    for task in raw_tasks:
        blocker_text = task.get("blocker")
        if blocker_text and str(blocker_text).strip().lower() not in ["none", "no", "hi", "hello", "completed"]:
            p_name = task["project_name"]
            if p_name not in project_blockers:
                project_blockers[p_name] = []
                
            start_date_str = task.get("start_date")
            days_active = 0
            if start_date_str:
                try:
                    start_date = datetime.strptime(start_date_str.split("T")[0], "%Y-%m-%d")
                    days_active = (datetime.now() - start_date).days
                except:
                    pass
            
            project_blockers[p_name].append({
                "id": f"blk-{task['id']}",
                "description": blocker_text,
                "date_created": start_date_str or "Unknown",
                "days_active": max(0, days_active),
                "client": project_clients.get(p_name, "adani")
            })
            
    # Process Projects
    projects = []
    for proj in raw_projects:
        p_name = proj["name"]
        assigned = project_allocations.get(p_name, [])
        blockers = project_blockers.get(p_name, [])
        client = project_clients.get(p_name, "adani")
        
        # Calculate timeline delay
        proj_status_raw = proj.get("status", "")
        end_date_str = proj.get("end_date")
        
        # Infer project status from tasks
        proj_tasks = [t for t in raw_tasks if t.get("project_name") == p_name]
        if proj_tasks:
            if all(t.get("status") == "Completed" for t in proj_tasks):
                proj_status_raw = "Completed"

        timeline_delay_days = 0
        
        if proj_status_raw != "Completed" and end_date_str:
            try:
                end_date = datetime.strptime(end_date_str.split("T")[0], "%Y-%m-%d")
                delay = (datetime.now() - end_date).days
                if delay > 0:
                    timeline_delay_days = delay
            except:
                pass

        # Calculate risk based on days active
        max_days = max([b["days_active"] for b in blockers]) if blockers else 0
        
        # Enforce > 6 days = Critical blocker
        if max_days > 6:
            ai_risk_level = "Critical"
        elif max_days > 0:
            ai_risk_level = "Medium"
        else:
            ai_risk_level = "Low"
        
        # Determine status
        status = "On Track"
        if proj_status_raw == "Completed":
            status = "Completed"
        elif timeline_delay_days > 10:
            status = "At Risk"
        elif timeline_delay_days > 0:
            status = "Delayed"
            
        projects.append({
            "id": f"prj-{proj['id']}",
            "project_name": p_name,
            "client": client,
            "status": status,
            "assigned_employees": assigned,
            "blockers": blockers,
            "timeline_delay_days": timeline_delay_days,
            "ai_risk_level": ai_risk_level
        })
        
    # Finalize employee project counts
    all_employees = []
    for emp in employee_map.values():
        emp["projects_count"] = len(emp["_active_projects"])
        clean_emp = {k: v for k, v in emp.items() if k != "_active_projects"}
        all_employees.append(clean_emp)
    
    return {
        "projects": projects,
        "allEmployees": all_employees,
        "availableClients": sorted(list(all_clients))
    }
