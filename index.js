require('dotenv').config();
const express = require('express');
const cors = require('cors');
const { Pool } = require('pg');

const app = express();
const PORT = process.env.PORT || 8005;

// ── Middleware ──────────────────────────────────────────────
app.use(cors({
  origin: '*',
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization']
}));
app.use(express.json());

// ── Database Connection ────────────────────────────────────
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: { rejectUnauthorized: false },
  connectionTimeoutMillis: 5000,
  idleTimeoutMillis: 30000,
  max: 10,
});

// Test database connectivity on startup
pool.query('SELECT 1')
  .then(() => console.log('✓ Database connection test successful'))
  .catch(err => console.error('✗ Database connection failed:', err.message));

// ── Helper: load all data from DB ──────────────────────────
async function loadData() {
  const client = await pool.connect();
  try {
    const [projects, allocations, teamMembers, tasks] = await Promise.all([
      client.query('SELECT * FROM projects'),
      client.query('SELECT * FROM allocations'),
      client.query('SELECT * FROM team_members'),
      client.query('SELECT * FROM tasks'),
    ]);
    return {
      tables: {
        projects:     { rows: projects.rows },
        allocations:  { rows: allocations.rows },
        team_members: { rows: teamMembers.rows },
        tasks:        { rows: tasks.rows },
      },
    };
  } catch (err) {
    console.error('✗ Error loading data:', err.message);
    return {
      tables: {
        projects:     { rows: [] },
        allocations:  { rows: [] },
        team_members: { rows: [] },
        tasks:        { rows: [] },
      },
    };
  } finally {
    client.release();
  }
}

// ── Routes ─────────────────────────────────────────────────
app.get('/', (_req, res) => {
  res.json({ status: 'ok', message: 'Cockpit backend is running' });
});

app.get('/health', (_req, res) => {
  res.json({ status: 'healthy' });
});

app.get('/api/dashboard', async (_req, res) => {
  try {
    const db = await loadData();
    const tables = db.tables || {};

    const rawProjects    = tables.projects?.rows     || [];
    const rawAllocations = tables.allocations?.rows   || [];
    const rawTeam        = tables.team_members?.rows  || [];
    const rawTasks       = tables.tasks?.rows         || [];

    const allClients = new Set();

    // ── Map project clients and statuses ──
    const projectClients  = {};
    const projectStatuses = {};
    for (const p of rawProjects) {
      const client = p.client || 'adani';
      const pName  = p.name;
      projectClients[pName]  = client;
      projectStatuses[pName] = p.status || '';
      allClients.add(client);
    }

    // ── Process Employees (case-insensitive matching) ──
    const employeeMap = {};
    for (const member of rawTeam) {
      const client = member.client || 'adani';
      allClients.add(client);
      const empKey = member.name.toLowerCase().trim();
      if (employeeMap[empKey]) {
        if (!employeeMap[empKey].clients.includes(client)) {
          employeeMap[empKey].clients.push(client);
        }
      } else {
        employeeMap[empKey] = {
          name: member.name,
          role: member.designation,
          projects_count: 0,
          clients: [client],
          _activeProjects: new Set(),
        };
      }
    }

    // ── Link allocations and tasks to employees ──
    const projectAllocations = {};

    function assignEmployeeToProject(empName, projName) {
      const empNameLower = empName.toLowerCase().trim();
      if (!employeeMap[empNameLower]) return;

      const emp = employeeMap[empNameLower];

      // Track for employee's project count (only if not completed)
      if (projectStatuses[projName] !== 'Completed') {
        emp._activeProjects.add(projName);
      }

      // Track cross-pollinating clients regardless of project completion
      const projClient = projectClients[projName];
      if (projClient && !emp.clients.includes(projClient)) {
        emp.clients.push(projClient);
      }

      // Track for project's assigned team
      if (!projectAllocations[projName]) {
        projectAllocations[projName] = [];
      }

      const currentAssigned = projectAllocations[projName].map(e => e.name);
      if (!currentAssigned.includes(emp.name)) {
        const cleanEmp = { ...emp };
        delete cleanEmp._activeProjects;
        projectAllocations[projName].push(cleanEmp);
      }
    }

    for (const alloc of rawAllocations) {
      assignEmployeeToProject(alloc.member_name, alloc.project_name);
    }

    for (const task of rawTasks) {
      if (task.assigned_to) {
        assignEmployeeToProject(task.assigned_to, task.project_name);
      }
    }

    // ── Process Blockers ──
    const projectBlockers = {};
    const ignoreBlockers = new Set(['none', 'no', 'hi', 'hello', 'completed']);

    for (const task of rawTasks) {
      const blockerText = task.blocker;
      if (blockerText && !ignoreBlockers.has(String(blockerText).trim().toLowerCase())) {
        const pName = task.project_name;
        if (!projectBlockers[pName]) {
          projectBlockers[pName] = [];
        }

        const startDateStr = task.start_date;
        let daysActive = 0;
        if (startDateStr) {
          try {
            const startDate = new Date(startDateStr.split('T')[0]);
            daysActive = Math.floor((Date.now() - startDate.getTime()) / (1000 * 60 * 60 * 24));
          } catch {
            // ignore parse errors
          }
        }

        projectBlockers[pName].push({
          id: `blk-${task.id}`,
          description: blockerText,
          date_created: startDateStr || 'Unknown',
          days_active: Math.max(0, daysActive),
          client: projectClients[pName] || 'adani',
        });
      }
    }

    // ── Process Projects ──
    const projects = [];
    for (const proj of rawProjects) {
      const pName    = proj.name;
      const assigned = projectAllocations[pName] || [];
      const blockers = projectBlockers[pName]    || [];
      const client   = projectClients[pName]     || 'adani';

      // Calculate timeline delay
      let projStatusRaw = proj.status || '';
      const endDateStr  = proj.end_date;

      // Infer project status from tasks
      const projTasks = rawTasks.filter(t => t.project_name === pName);
      if (projTasks.length > 0) {
        if (projTasks.every(t => t.status === 'Completed')) {
          projStatusRaw = 'Completed';
        }
      }

      let timelineDelayDays = 0;
      if (projStatusRaw !== 'Completed' && endDateStr) {
        try {
          const endDate = new Date(endDateStr.split('T')[0]);
          const delay   = Math.floor((Date.now() - endDate.getTime()) / (1000 * 60 * 60 * 24));
          if (delay > 0) timelineDelayDays = delay;
        } catch {
          // ignore parse errors
        }
      }

      // Calculate risk based on days active
      const maxDays = blockers.length > 0
        ? Math.max(...blockers.map(b => b.days_active))
        : 0;

      let aiRiskLevel;
      if (maxDays > 6)      aiRiskLevel = 'Critical';
      else if (maxDays > 0) aiRiskLevel = 'Medium';
      else                  aiRiskLevel = 'Low';

      // Determine status
      let status = 'On Track';
      if (projStatusRaw === 'Completed')    status = 'Completed';
      else if (timelineDelayDays > 10)      status = 'At Risk';
      else if (timelineDelayDays > 0)       status = 'Delayed';

      projects.push({
        id: `prj-${proj.id}`,
        project_name: pName,
        client,
        status,
        assigned_employees: assigned,
        blockers,
        timeline_delay_days: timelineDelayDays,
        ai_risk_level: aiRiskLevel,
      });
    }

    // ── Finalize employee project counts ──
    const allEmployees = [];
    for (const emp of Object.values(employeeMap)) {
      emp.projects_count = emp._activeProjects.size;
      const cleanEmp = { ...emp };
      delete cleanEmp._activeProjects;
      allEmployees.push(cleanEmp);
    }

    res.json({
      projects,
      allEmployees,
      availableClients: [...allClients].sort(),
    });
  } catch (err) {
    console.error('✗ Dashboard error:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// ── Start Server ───────────────────────────────────────────
app.listen(PORT, () => {
  console.log(`🚀 Cockpit backend running on http://localhost:${PORT}`);
});
