require('dotenv').config();
const fs   = require('fs');
const path = require('path');
const { Pool } = require('pg');

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: { rejectUnauthorized: false },
});

const DATA_PATH = path.join(__dirname, 'p', 'portal_full_db_snapshot.json');

async function seed() {
  console.log('Connecting to database...');
  const client = await pool.connect();

  try {
    // ── Create tables if they don't exist ──
    console.log('Initializing DB schemas...');
    await client.query(`
      CREATE TABLE IF NOT EXISTS projects (
        id SERIAL PRIMARY KEY,
        name TEXT,
        sprint TEXT,
        status TEXT,
        start_date TEXT,
        end_date TEXT,
        total_story_pts REAL,
        burned_story_pts REAL,
        est_hours REAL,
        hours_burned REAL,
        description TEXT,
        tech_stack TEXT,
        department TEXT,
        owner TEXT,
        business_user TEXT,
        client TEXT,
        custom_metrics TEXT,
        pdd_pdf_file TEXT,
        brd_pdf_file TEXT
      );

      CREATE TABLE IF NOT EXISTS allocations (
        id SERIAL PRIMARY KEY,
        client TEXT,
        member_name TEXT,
        project_name TEXT,
        hours REAL
      );

      CREATE TABLE IF NOT EXISTS team_members (
        id SERIAL PRIMARY KEY,
        client TEXT,
        username TEXT,
        name TEXT,
        designation TEXT,
        availability REAL,
        tech TEXT,
        location TEXT
      );

      CREATE TABLE IF NOT EXISTS tasks (
        id SERIAL PRIMARY KEY,
        project_name TEXT,
        task_name TEXT,
        status TEXT,
        assigned_to TEXT,
        hours_allocated REAL,
        start_date TEXT,
        end_date TEXT,
        priority TEXT,
        blocker TEXT,
        client TEXT,
        phase TEXT,
        completed_at TEXT
      );
    `);

    // ── Load JSON snapshot ──
    console.log(`Loading data from ${DATA_PATH}...`);
    const raw  = fs.readFileSync(DATA_PATH, 'utf-8');
    const data = JSON.parse(raw);
    const tables = data.tables || {};

    // ── Clear existing data ──
    console.log('Clearing existing data...');
    await client.query('DELETE FROM projects');
    await client.query('DELETE FROM allocations');
    await client.query('DELETE FROM team_members');
    await client.query('DELETE FROM tasks');

    // ── Insert projects ──
    const projectsData = (tables.projects?.rows) || [];
    console.log(`Inserting ${projectsData.length} projects...`);
    for (const p of projectsData) {
      await client.query(
        `INSERT INTO projects (id, name, sprint, status, start_date, end_date, total_story_pts, burned_story_pts, est_hours, hours_burned, description, tech_stack, department, owner, business_user, client, custom_metrics, pdd_pdf_file, brd_pdf_file)
         VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19)`,
        [p.id, p.name, p.sprint, p.status, p.start_date, p.end_date, p.total_story_pts, p.burned_story_pts, p.est_hours, p.hours_burned, p.description, p.tech_stack, p.department, p.owner, p.business_user, p.client, p.custom_metrics, p.pdd_pdf_file, p.brd_pdf_file]
      );
    }

    // ── Insert allocations ──
    const allocData = (tables.allocations?.rows) || [];
    console.log(`Inserting ${allocData.length} allocations...`);
    for (const a of allocData) {
      await client.query(
        `INSERT INTO allocations (id, client, member_name, project_name, hours)
         VALUES ($1,$2,$3,$4,$5)`,
        [a.id, a.client, a.member_name, a.project_name, a.hours]
      );
    }

    // ── Insert team members ──
    const teamData = (tables.team_members?.rows) || [];
    console.log(`Inserting ${teamData.length} team members...`);
    for (const t of teamData) {
      await client.query(
        `INSERT INTO team_members (id, client, username, name, designation, availability, tech, location)
         VALUES ($1,$2,$3,$4,$5,$6,$7,$8)`,
        [t.id, t.client, t.username, t.name, t.designation, t.availability, t.tech, t.location]
      );
    }

    // ── Insert tasks ──
    const tasksData = (tables.tasks?.rows) || [];
    console.log(`Inserting ${tasksData.length} tasks...`);
    for (const t of tasksData) {
      await client.query(
        `INSERT INTO tasks (id, project_name, task_name, status, assigned_to, hours_allocated, start_date, end_date, priority, blocker, client, phase, completed_at)
         VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)`,
        [t.id, t.project_name, t.task_name, t.status, t.assigned_to, t.hours_allocated, t.start_date, t.end_date, t.priority, t.blocker, t.client, t.phase, t.completed_at]
      );
    }

    console.log('✓ Database seeded successfully!');
  } catch (err) {
    console.error('✗ Seeding failed:', err);
  } finally {
    client.release();
    await pool.end();
  }
}

seed();
