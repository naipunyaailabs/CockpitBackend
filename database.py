import os
import sys
from sqlalchemy import create_engine, Column, Integer, String, Float, Text, pool
from sqlalchemy.orm import declarative_base, sessionmaker

print("Initializing database module...", file=sys.stderr)

# Allow the database URL to come from an environment variable for deployment.
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://neondb_owner:npg_F5DQfo7YLPzT@ep-green-wave-ate7kl18-pooler.c-9.us-east-1.aws.neon.tech/neondb?sslmode=require"
)

print(f"Database URL configured (length: {len(DATABASE_URL)})", file=sys.stderr)

# Try to create engine and test connection with timeout
engine = None
SessionLocal = None
Base = declarative_base()

try:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=3600,
        connect_args={"connect_timeout": 5, "options": "-c statement_timeout=10000"},
        echo=False
    )
    # Test the connection
    with engine.connect() as conn:
        result = conn.execute("SELECT 1")
        print(f"✓ Database connection test successful", file=sys.stderr)
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    print(f"✓ Database engine created successfully", file=sys.stderr)
except Exception as e:
    print(f"✗ Database connection failed: {str(e)[:200]}", file=sys.stderr)
    print(f"✗ Backend will run in read-only mode without database", file=sys.stderr)
    SessionLocal = None
    engine = None

class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    sprint = Column(String)
    status = Column(String)
    start_date = Column(String)
    end_date = Column(String)
    total_story_pts = Column(Float)
    burned_story_pts = Column(Float)
    est_hours = Column(Float)
    hours_burned = Column(Float)
    description = Column(Text)
    tech_stack = Column(String)
    department = Column(String)
    owner = Column(String)
    business_user = Column(String)
    client = Column(String)
    custom_metrics = Column(Text)
    pdd_pdf_file = Column(String)
    brd_pdf_file = Column(String)

class Allocation(Base):
    __tablename__ = "allocations"
    id = Column(Integer, primary_key=True, index=True)
    client = Column(String)
    member_name = Column(String)
    project_name = Column(String)
    hours = Column(Float)

class TeamMember(Base):
    __tablename__ = "team_members"
    id = Column(Integer, primary_key=True, index=True)
    client = Column(String)
    username = Column(String)
    name = Column(String)
    designation = Column(String)
    availability = Column(Float)
    tech = Column(String)
    location = Column(String)

class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, index=True)
    project_name = Column(String)
    task_name = Column(String)
    status = Column(String)
    assigned_to = Column(String)
    hours_allocated = Column(Float)
    start_date = Column(String)
    end_date = Column(String)
    priority = Column(String)
    blocker = Column(Text)
    client = Column(String)
    phase = Column(String)
    completed_at = Column(String)

def init_db():
    Base.metadata.create_all(bind=engine)
