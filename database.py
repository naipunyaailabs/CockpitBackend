from sqlalchemy import create_engine, Column, Integer, String, Float, Text
from sqlalchemy.orm import declarative_base, sessionmaker

# The channel_binding query param might cause issues with some psycopg2 versions.
# If it fails, we can strip it, but we'll try the provided URL first.
DATABASE_URL = "postgresql://neondb_owner:npg_F5DQfo7YLPzT@ep-green-wave-ate7kl18-pooler.c-9.us-east-1.aws.neon.tech/neondb?sslmode=require"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

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
