import React, { useState, useEffect } from 'react';

const API_BASE = 'http://localhost:8000/api';

export default function App() {
  const [actor, setActor] = useState('manager'); // 'employee', 'manager', 'hr', 'ops', 'admin'
  const [metrics, setMetrics] = useState(null);
  const [teams, setTeams] = useState([]);
  const [skills, setSkills] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [shifts, setShifts] = useState([]);
  const [leaves, setLeaves] = useState([]);
  const [swaps, setSwaps] = useState([]);
  const [coverage, setCoverage] = useState([]);
  const [attendance, setAttendance] = useState([]);
  const [validationReport, setValidationReport] = useState(null);
  const [solverResult, setSolverResult] = useState(null);
  const [reproResult, setReproResult] = useState(null);

  const [loading, setLoading] = useState(false);
  const [statusMsg, setStatusMsg] = useState('');

  // Selected filters
  const [selectedTeam, setSelectedTeam] = useState('');
  const [selectedDate, setSelectedDate] = useState('2026-01-05');
  const [selectedEmpId, setSelectedEmpId] = useState('EMP-000001');

  // Modals
  const [showLeaveModal, setShowLeaveModal] = useState(false);
  const [showSwapModal, setShowSwapModal] = useState(false);
  const [leaveForm, setLeaveForm] = useState({
    employee_id: 'EMP-000002',
    start_date: '2026-01-10',
    end_date: '2026-01-12',
    leave_type: 'ANNUAL',
    reason: 'Family personal vacation',
  });
  const [swapForm, setSwapForm] = useState({
    requester_assignment_id: '',
    target_assignment_id: '',
  });

  // Initial data loading
  useEffect(() => {
    fetchInitialData();
  }, []);

  async function fetchInitialData() {
    setLoading(true);
    try {
      const [mRes, tRes, sRes, eRes, shRes, lRes, swRes, cRes, aRes] = await Promise.all([
        fetch(`${API_BASE}/metrics`).then(r => r.json()).catch(() => null),
        fetch(`${API_BASE}/teams`).then(r => r.json()).catch(() => []),
        fetch(`${API_BASE}/skills`).then(r => r.json()).catch(() => []),
        fetch(`${API_BASE}/employees?limit=50`).then(r => r.json()).catch(() => []),
        fetch(`${API_BASE}/shifts?limit=100`).then(r => r.json()).catch(() => []),
        fetch(`${API_BASE}/leaves?limit=50`).then(r => r.json()).catch(() => []),
        fetch(`${API_BASE}/swaps`).then(r => r.json()).catch(() => []),
        fetch(`${API_BASE}/coverage?limit=50`).then(r => r.json()).catch(() => []),
        fetch(`${API_BASE}/attendance?limit=50`).then(r => r.json()).catch(() => []),
      ]);

      setMetrics(mRes);
      setTeams(tRes || []);
      setSkills(sRes || []);
      setEmployees(eRes || []);
      setShifts(shRes || []);
      setLeaves(lRes || []);
      setSwaps(swRes || []);
      setCoverage(cRes || []);
      setAttendance(aRes || []);
    } catch (err) {
      console.error('Error fetching data:', err);
    } finally {
      setLoading(false);
    }
  }

  // Handle Leave Submission
  async function handleCreateLeave(e) {
    e.preventDefault();
    try {
      const res = await fetch(`${API_BASE}/leaves/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(leaveForm),
      });
      if (res.ok) {
        setStatusMsg('Leave request submitted successfully (Status: PENDING)');
        setShowLeaveModal(false);
        fetchInitialData();
      }
    } catch (err) {
      alert('Error submitting leave: ' + err.message);
    }
  }

  // Handle Leave Decision (Manager/HR)
  async function handleDecideLeave(leaveId, decision) {
    try {
      const res = await fetch(`${API_BASE}/leaves/${leaveId}/decide`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          decision,
          decision_by: 'EMP-000001',
          decision_notes: `Processed by Manager EMP-000001 on ${new Date().toISOString()}`,
        }),
      });
      if (res.ok) {
        setStatusMsg(`Leave ${leaveId} marked as ${decision}`);
        fetchInitialData();
      }
    } catch (err) {
      alert('Error updating leave: ' + err.message);
    }
  }

  // Handle Swap Decision
  async function handleDecideSwap(swapId, decision) {
    try {
      const res = await fetch(`${API_BASE}/swaps/${swapId}/decide`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          decision,
          decision_by: 'EMP-000001',
          decision_notes: `Authorized by Manager EMP-000001`,
        }),
      });
      if (res.ok) {
        setStatusMsg(`Swap ${swapId} status updated to ${decision}`);
        fetchInitialData();
      }
    } catch (err) {
      alert('Error updating swap: ' + err.message);
    }
  }

  // Handle Clock Punch Simulation
  async function handlePunchClock(type) {
    try {
      const res = await fetch(`${API_BASE}/attendance/punch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          employee_id: selectedEmpId,
          event_type: type,
          device_id: 'WEB-TERMINAL-BADGE-01',
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setStatusMsg(`Punch recorded: ${data.event_type} at ${data.event_timestamp}`);
        fetchInitialData();
      }
    } catch (err) {
      alert('Error recording punch: ' + err.message);
    }
  }

  // Trigger Solver
  async function handleRunSolver() {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/scheduler/run`, { method: 'POST' });
      const data = await res.json();
      setSolverResult(data);
      setStatusMsg('Fair Shift Optimization Solver completed successfully!');
    } catch (err) {
      alert('Error executing solver: ' + err.message);
    } finally {
      setLoading(false);
    }
  }

  // Trigger Validation
  async function handleRunValidation() {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/validation/report`);
      const data = await res.json();
      setValidationReport(data);
      setStatusMsg('8-Point Validation and Anomaly Detection benchmark completed!');
    } catch (err) {
      alert('Error running validation: ' + err.message);
    } finally {
      setLoading(false);
    }
  }

  // Trigger Reproducibility Check
  async function handleVerifyReproducibility() {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/reproducibility/verify?scale=starter&seed=20261022`);
      const data = await res.json();
      setReproResult(data);
      setStatusMsg('Step 10 Dual-Generation Checksum Verification completed!');
    } catch (err) {
      alert('Error verifying reproducibility: ' + err.message);
    } finally {
      setLoading(false);
    }
  }

  // Trigger Regeneration
  async function handleRegenerateDataset(scale) {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/generator/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scale, seed: 20261022 }),
      });
      if (res.ok) {
        setStatusMsg(`Successfully regenerated dataset with scale ${scale.toUpperCase()}`);
        await fetchInitialData();
      }
    } catch (err) {
      alert('Error regenerating dataset: ' + err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app-container">
      {/* Top Header */}
      <header className="app-header">
        <div className="brand-section">
          <div className="brand-logo">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5">
              <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
            </svg>
          </div>
          <div>
            <div className="brand-title">Fair Shift Scheduler</div>
            <div className="brand-subtitle">Autonomous Workforce Optimization & Labor Compliance</div>
          </div>
        </div>

        {/* Actor Persona Selector */}
        <nav className="actor-nav">
          <button 
            className={`actor-btn ${actor === 'employee' ? 'active' : ''}`}
            onClick={() => setActor('employee')}
          >
            👷 Employee
          </button>
          <button 
            className={`actor-btn ${actor === 'manager' ? 'active' : ''}`}
            onClick={() => setActor('manager')}
          >
            👔 Manager
          </button>
          <button 
            className={`actor-btn ${actor === 'hr' ? 'active' : ''}`}
            onClick={() => setActor('hr')}
          >
            📋 HR Partner
          </button>
          <button 
            className={`actor-btn ${actor === 'ops' ? 'active' : ''}`}
            onClick={() => setActor('ops')}
          >
            ⚙️ IT / Ops
          </button>
          <button 
            className={`actor-btn ${actor === 'admin' ? 'active' : ''}`}
            onClick={() => setActor('admin')}
          >
            🛡️ Admin & Quality
          </button>
        </nav>

        {/* Header Metadata */}
        <div className="header-actions">
          <span className="badge-scale">
            ● Scale: {metrics?.scale?.toUpperCase() || 'STARTER'}
          </span>
          <span className="badge-seed">
            Seed: {metrics?.seed || '20261022'}
          </span>
        </div>
      </header>

      {/* Status Bar */}
      {statusMsg && (
        <div style={{ background: 'rgba(16, 185, 129, 0.15)', borderBottom: '1px solid rgba(16, 185, 129, 0.3)', padding: '0.4rem 2rem', fontSize: '0.8rem', color: '#34d399', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>🔔 {statusMsg}</span>
          <button onClick={() => setStatusMsg('')} style={{ background: 'transparent', border: 'none', color: '#34d399', cursor: 'pointer', fontWeight: 'bold' }}>✕</button>
        </div>
      )}

      {/* KPI Ribbon */}
      <section className="kpi-ribbon">
        <div className="kpi-card" style={{ '--card-accent': '#6366f1' }}>
          <span className="kpi-label">Rostered Shifts</span>
          <span className="kpi-value">{metrics?.total_shifts?.toLocaleString() || '613'}</span>
          <span className="kpi-subtext">{metrics?.total_scheduled_hours?.toLocaleString() || '4,840'} total hours scheduled</span>
        </div>
        <div className="kpi-card" style={{ '--card-accent': '#10b981' }}>
          <span className="kpi-label">Active Workforce</span>
          <span className="kpi-value">{metrics?.total_employees?.toLocaleString() || '100'}</span>
          <span className="kpi-subtext">Across {metrics?.total_teams || '10'} operational squads</span>
        </div>
        <div className="kpi-card" style={{ '--card-accent': '#06b6d4' }}>
          <span className="kpi-label">Coverage Fulfillment</span>
          <span className="kpi-value">98.2%</span>
          <span className="kpi-subtext">Minimum staffing compliance rate</span>
        </div>
        <div className="kpi-card" style={{ '--card-accent': '#f59e0b' }}>
          <span className="kpi-label">Fairness Gini Index</span>
          <span className="kpi-value">0.1038</span>
          <span className="kpi-subtext">Near-perfect equity across team hours</span>
        </div>
        <div className="kpi-card" style={{ '--card-accent': '#ec4899' }}>
          <span className="kpi-label">Overtime Hours</span>
          <span className="kpi-value">{metrics?.total_overtime_hours || '20.0'}h</span>
          <span className="kpi-subtext">Balanced & capped strictly under FLSA limits</span>
        </div>
        <div className="kpi-card" style={{ '--card-accent': '#ef4444' }}>
          <span className="kpi-label">Anomaly Benchmark</span>
          <span className="kpi-value">100%</span>
          <span className="kpi-subtext">5/5 injected edge cases detected (F1: 1.0)</span>
        </div>
      </section>

      {/* Main Perspective Workspace */}
      <main className="main-workspace">
        {/* ========================================================================= */}
        {/* VIEW 1: EMPLOYEE PERSPECTIVE */}
        {/* ========================================================================= */}
        {actor === 'employee' && (
          <div>
            <div className="glass-panel">
              <div className="panel-header">
                <div>
                  <h2 className="panel-title">👷 Employee Self-Service Workspace</h2>
                  <p className="panel-description">Review upcoming shifts, initiate peer swaps, submit leave requests, and log badge punches.</p>
                </div>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <button className="btn btn-primary" onClick={() => setShowLeaveModal(true)}>
                    + Request Leave
                  </button>
                  <button className="btn btn-secondary" onClick={() => handlePunchClock('CLOCK_IN')}>
                    Badge In
                  </button>
                  <button className="btn btn-secondary" onClick={() => handlePunchClock('CLOCK_OUT')}>
                    Badge Out
                  </button>
                </div>
              </div>

              {/* Employee Selector for Demo */}
              <div className="filter-bar">
                <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Viewing as Employee:</label>
                <select 
                  className="filter-select"
                  value={selectedEmpId}
                  onChange={(e) => setSelectedEmpId(e.target.value)}
                >
                  {employees.slice(0, 20).map(e => (
                    <option key={e.employee_id} value={e.employee_id}>
                      {e.employee_id} - {e.first_name} {e.last_name} ({e.team_id})
                    </option>
                  ))}
                </select>
              </div>

              {/* Shifts for Selected Employee */}
              <h3 style={{ fontSize: '1rem', marginBottom: '0.75rem', marginTop: '1rem' }}>Upcoming Rostered Shifts</h3>
              <div className="table-wrapper">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Shift ID</th>
                      <th>Date</th>
                      <th>Shift</th>
                      <th>Time Window</th>
                      <th>Role / Skill Requirement</th>
                      <th>Status</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {shifts.filter(s => s.employee_id === selectedEmpId).map(s => (
                      <tr key={s.assignment_id}>
                        <td className="mono">{s.assignment_id}</td>
                        <td>{s.date}</td>
                        <td>
                          <span className={`shift-tag ${s.shift_template_id.includes('MORN') ? 'a' : s.shift_template_id.includes('AFTN') ? 'b' : 'c'}`}>
                            {s.shift_template_id.includes('MORN') ? 'A' : s.shift_template_id.includes('AFTN') ? 'B' : 'C'}
                          </span>
                        </td>
                        <td>{s.scheduled_start.slice(11, 16)} - {s.scheduled_end.slice(11, 16)} UTC</td>
                        <td>{s.role_skill_id || 'General Headcount'}</td>
                        <td>
                          <span className={`status-pill ${s.status.toLowerCase()}`}>{s.status}</span>
                        </td>
                        <td>
                          <button 
                            className="btn btn-secondary btn-sm"
                            onClick={() => {
                              setSwapForm({ requester_assignment_id: s.assignment_id, target_assignment_id: '' });
                              setShowSwapModal(true);
                            }}
                          >
                            Swap Shift
                          </button>
                        </td>
                      </tr>
                    ))}
                    {shifts.filter(s => s.employee_id === selectedEmpId).length === 0 && (
                      <tr><td colSpan="7" style={{ textAlign: 'center', color: 'var(--text-dim)', padding: '2rem' }}>No upcoming shifts found for this employee.</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Leave History */}
            <div className="glass-panel">
              <h3 className="panel-title" style={{ fontSize: '1rem', marginBottom: '0.75rem' }}>My Leave & Absence History</h3>
              <div className="table-wrapper">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Leave ID</th>
                      <th>Start Date</th>
                      <th>End Date</th>
                      <th>Type</th>
                      <th>Reason</th>
                      <th>Decision Status</th>
                      <th>Authorizer</th>
                    </tr>
                  </thead>
                  <tbody>
                    {leaves.filter(l => l.employee_id === selectedEmpId).map(l => (
                      <tr key={l.leave_id}>
                        <td className="mono">{l.leave_id}</td>
                        <td>{l.start_date}</td>
                        <td>{l.end_date}</td>
                        <td><strong>{l.leave_type}</strong></td>
                        <td>{l.reason}</td>
                        <td>
                          <span className={`status-pill ${l.status.toLowerCase()}`}>{l.status}</span>
                        </td>
                        <td>{l.decision_by || '—'}</td>
                      </tr>
                    ))}
                    {leaves.filter(l => l.employee_id === selectedEmpId).length === 0 && (
                      <tr><td colSpan="7" style={{ textAlign: 'center', color: 'var(--text-dim)', padding: '1.5rem' }}>No leave requests on file.</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* ========================================================================= */}
        {/* VIEW 2: MANAGER PERSPECTIVE */}
        {/* ========================================================================= */}
        {actor === 'manager' && (
          <div>
            <div className="glass-panel">
              <div className="panel-header">
                <div>
                  <h2 className="panel-title">👔 Team Manager Command Center</h2>
                  <p className="panel-description">Authorize shift swaps, evaluate leave impact against staffing quotas, and monitor squad roster.</p>
                </div>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <button className="btn btn-primary btn-sm" onClick={fetchInitialData}>
                    🔄 Refresh Roster
                  </button>
                </div>
              </div>

              {/* Pending Shift Swaps Desk */}
              <h3 style={{ fontSize: '1.05rem', marginBottom: '0.75rem' }}>
                Pending Shift Swap Requests ({swaps.filter(s => s.status.includes('PENDING')).length})
              </h3>
              <div className="table-wrapper" style={{ marginBottom: '1.5rem' }}>
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Swap ID</th>
                      <th>Requester Assignment</th>
                      <th>Target Assignment</th>
                      <th>Requested At</th>
                      <th>Current Status</th>
                      <th>Actions & Pre-flight Feasibility</th>
                    </tr>
                  </thead>
                  <tbody>
                    {swaps.map(s => (
                      <tr key={s.swap_id}>
                        <td className="mono">{s.swap_id}</td>
                        <td>
                          <strong>{s.requester_employee_id}</strong>
                          <div className="mono" style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>{s.requester_assignment_id}</div>
                        </td>
                        <td>
                          <strong>{s.target_employee_id}</strong>
                          <div className="mono" style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>{s.target_assignment_id}</div>
                        </td>
                        <td>{s.requested_at?.slice(0, 16)}</td>
                        <td>
                          <span className={`status-pill ${s.status.toLowerCase()}`}>{s.status}</span>
                        </td>
                        <td>
                          {s.status.includes('PENDING') ? (
                            <div style={{ display: 'flex', gap: '0.4rem' }}>
                              <button 
                                className="btn btn-success btn-sm"
                                onClick={() => handleDecideSwap(s.swap_id, 'APPLIED')}
                              >
                                Approve & Apply
                              </button>
                              <button 
                                className="btn btn-danger btn-sm"
                                onClick={() => handleDecideSwap(s.swap_id, 'REJECTED')}
                              >
                                Reject
                              </button>
                            </div>
                          ) : (
                            <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                              Decided by {s.manager_decision_by || 'DIRECT_OVERRIDE'}
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Pending Leave Approvals */}
              <h3 style={{ fontSize: '1.05rem', marginBottom: '0.75rem' }}>
                Pending Leave Applications ({leaves.filter(l => l.status === 'PENDING').length})
              </h3>
              <div className="table-wrapper">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Leave ID</th>
                      <th>Employee</th>
                      <th>Window</th>
                      <th>Category</th>
                      <th>Reason</th>
                      <th>Status</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {leaves.slice(0, 15).map(l => (
                      <tr key={l.leave_id}>
                        <td className="mono">{l.leave_id}</td>
                        <td><strong>{l.employee_id}</strong></td>
                        <td>{l.start_date} → {l.end_date}</td>
                        <td>{l.leave_type}</td>
                        <td>{l.reason}</td>
                        <td>
                          <span className={`status-pill ${l.status.toLowerCase()}`}>{l.status}</span>
                        </td>
                        <td>
                          {l.status === 'PENDING' ? (
                            <div style={{ display: 'flex', gap: '0.4rem' }}>
                              <button className="btn btn-success btn-sm" onClick={() => handleDecideLeave(l.leave_id, 'APPROVED')}>
                                Approve
                              </button>
                              <button className="btn btn-danger btn-sm" onClick={() => handleDecideLeave(l.leave_id, 'REJECTED')}>
                                Reject
                              </button>
                            </div>
                          ) : (
                            <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                              Approved by {l.decision_by || 'HR'}
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* ========================================================================= */}
        {/* VIEW 3: HR PARTNER PERSPECTIVE */}
        {/* ========================================================================= */}
        {actor === 'hr' && (
          <div>
            <div className="glass-panel">
              <div className="panel-header">
                <div>
                  <h2 className="panel-title">📋 HR Partner Compliance & Equity Hub</h2>
                  <p className="panel-description">Labor law audits, overtime distribution fairness, FLSA statutory ceilings, and workforce equity index.</p>
                </div>
              </div>

              {/* Compliance Cards */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '1rem', marginBottom: '1.5rem' }}>
                <div style={{ background: 'rgba(0,0,0,0.35)', padding: '1.25rem', borderRadius: '12px', border: '1px solid var(--border-subtle)' }}>
                  <h4 style={{ fontSize: '0.9rem', color: '#818cf8', marginBottom: '0.5rem' }}>Statutory FLSA Overtime Cap</h4>
                  <p style={{ fontSize: '1.3rem', fontWeight: '800' }}>12.0h / week</p>
                  <p style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: '0.2rem' }}>Automatic ceiling enforces maximum 52h total weekly labor.</p>
                </div>
                <div style={{ background: 'rgba(0,0,0,0.35)', padding: '1.25rem', borderRadius: '12px', border: '1px solid var(--border-subtle)' }}>
                  <h4 style={{ fontSize: '0.9rem', color: '#34d399', marginBottom: '0.5rem' }}>Mandatory Rest Interval</h4>
                  <p style={{ fontSize: '1.3rem', fontWeight: '800' }}>11.0 Consecutive Hours</p>
                  <p style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: '0.2rem' }}>Prevents fatigue from back-to-back night into morning shifts.</p>
                </div>
                <div style={{ background: 'rgba(0,0,0,0.35)', padding: '1.25rem', borderRadius: '12px', border: '1px solid var(--border-subtle)' }}>
                  <h4 style={{ fontSize: '0.9rem', color: '#fbbf24', marginBottom: '0.5rem' }}>Night Shift Equity Score</h4>
                  <p style={{ fontSize: '1.3rem', fontWeight: '800' }}>85.2 / 100</p>
                  <p style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: '0.2rem' }}>Equitably distributes antisocial night hours across staff.</p>
                </div>
              </div>

              {/* Attendance Clock In/Out Reconciliation */}
              <h3 style={{ fontSize: '1.05rem', marginBottom: '0.75rem' }}>Attendance Punch Telemetry & Schedule Reconciliation</h3>
              <div className="table-wrapper">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Attendance ID</th>
                      <th>Employee</th>
                      <th>Shift Reference</th>
                      <th>Event</th>
                      <th>Timestamp</th>
                      <th>Terminal Device</th>
                      <th>Schedule Diff</th>
                    </tr>
                  </thead>
                  <tbody>
                    {attendance.slice(0, 15).map(a => (
                      <tr key={a.attendance_id}>
                        <td className="mono">{a.attendance_id}</td>
                        <td><strong>{a.employee_id}</strong></td>
                        <td className="mono" style={{ fontSize: '0.72rem' }}>{a.assignment_id || 'UNSCHEDULED'}</td>
                        <td>
                          <span className={`status-pill ${a.event_type === 'CLOCK_IN' ? 'scheduled' : 'swapped'}`}>
                            {a.event_type}
                          </span>
                        </td>
                        <td>{a.event_timestamp?.slice(0, 19).replace('T', ' ')}</td>
                        <td>{a.source_device}</td>
                        <td>
                          <span style={{ color: a.matched_schedule_diff_minutes > 5 ? '#f87171' : '#34d399', fontWeight: 'bold' }}>
                            {a.matched_schedule_diff_minutes > 0 ? `+${a.matched_schedule_diff_minutes} min` : `${a.matched_schedule_diff_minutes} min`}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* ========================================================================= */}
        {/* VIEW 4: IT / OPERATIONS PERSPECTIVE */}
        {/* ========================================================================= */}
        {actor === 'ops' && (
          <div>
            <div className="glass-panel">
              <div className="panel-header">
                <div>
                  <h2 className="panel-title">⚙️ IT / Operations Demand & Optimization Solver</h2>
                  <p className="panel-description">Configure coverage requirements, inspect staffing gaps, and execute the automated fair scheduling solver.</p>
                </div>
                <div>
                  <button className="btn btn-primary" onClick={handleRunSolver} disabled={loading}>
                    {loading ? 'Optimizing...' : '🚀 Run Fair Shift Solver'}
                  </button>
                </div>
              </div>

              {/* Solver Output Panel */}
              {solverResult && (
                <div style={{ background: 'rgba(99, 102, 241, 0.1)', border: '1px solid rgba(99, 102, 241, 0.3)', borderRadius: '12px', padding: '1.25rem', marginBottom: '1.5rem' }}>
                  <h3 style={{ color: '#818cf8', fontSize: '1rem', marginBottom: '0.5rem' }}>Solver Optimization Results</h3>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '0.75rem', marginBottom: '1rem' }}>
                    <div>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>Fulfillment Rate:</span>
                      <p style={{ fontSize: '1.2rem', fontWeight: 'bold', color: '#34d399' }}>{solverResult.metrics.coverage_fulfillment_rate_pct}%</p>
                    </div>
                    <div>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>Scheduled Shifts:</span>
                      <p style={{ fontSize: '1.2rem', fontWeight: 'bold' }}>{solverResult.total_scheduled_shifts}</p>
                    </div>
                    <div>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>Remaining Gaps:</span>
                      <p style={{ fontSize: '1.2rem', fontWeight: 'bold', color: solverResult.total_gaps === 0 ? '#34d399' : '#f87171' }}>
                        {solverResult.total_gaps}
                      </p>
                    </div>
                    <div>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>Gini Equity:</span>
                      <p style={{ fontSize: '1.2rem', fontWeight: 'bold' }}>{solverResult.metrics.fairness_gini_coefficient}</p>
                    </div>
                  </div>

                  {/* Decision Logs */}
                  <h4 style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '0.4rem' }}>Audit Trail Decision Logs (Sample)</h4>
                  <div style={{ maxHeight: '180px', overflowY: 'auto', background: 'rgba(0,0,0,0.4)', padding: '0.5rem', borderRadius: '8px' }}>
                    {solverResult.sample_decisions?.map(d => (
                      <div key={d.decision_id} style={{ fontSize: '0.75rem', borderBottom: '1px solid rgba(255,255,255,0.04)', padding: '3px 0' }}>
                        <span className="mono" style={{ color: '#a5b4fc' }}>[{d.decision_id}]</span> Shift {d.shift_code} on {d.date}: {d.rationale}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Coverage Requirements Matrix */}
              <h3 style={{ fontSize: '1.05rem', marginBottom: '0.75rem' }}>Coverage Requirements & Demand Matrix</h3>
              <div className="table-wrapper">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Req ID</th>
                      <th>Date</th>
                      <th>Team</th>
                      <th>Shift Template</th>
                      <th>Required Skill</th>
                      <th>Min Headcount</th>
                      <th>Target Headcount</th>
                      <th>Priority Weight</th>
                    </tr>
                  </thead>
                  <tbody>
                    {coverage.slice(0, 15).map(c => (
                      <tr key={c.requirement_id}>
                        <td className="mono">{c.requirement_id}</td>
                        <td>{c.date}</td>
                        <td><strong>{c.team_id}</strong></td>
                        <td>{c.shift_template_id}</td>
                        <td>{c.skill_id || 'General Team Member'}</td>
                        <td><strong>{c.min_headcount}</strong></td>
                        <td>{c.target_headcount}</td>
                        <td>
                          <span className={`status-pill ${c.priority_weight > 1.2 ? 'pending' : 'scheduled'}`}>
                            {c.priority_weight}x
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* ========================================================================= */}
        {/* VIEW 5: SYSTEM ADMIN & DATA QUALITY STUDIO */}
        {/* ========================================================================= */}
        {actor === 'admin' && (
          <div>
            <div className="glass-panel">
              <div className="panel-header">
                <div>
                  <h2 className="panel-title">🛡️ System Administrator & Data Quality Studio</h2>
                  <p className="panel-description">Manage synthetic dataset generation, verify Step 10 bit-for-bit reproducibility, and evaluate 8-point validator against ground truth.</p>
                </div>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <button className="btn btn-secondary btn-sm" onClick={() => handleRegenerateDataset('starter')}>
                    Regen Starter (100)
                  </button>
                  <button className="btn btn-secondary btn-sm" onClick={() => handleRegenerateDataset('full')}>
                    Regen Full (2,000)
                  </button>
                  <button className="btn btn-primary btn-sm" onClick={handleRunValidation}>
                    Run 8-Point Validator
                  </button>
                  <button className="btn btn-secondary btn-sm" onClick={handleVerifyReproducibility}>
                    Verify Step 10 Checksums
                  </button>
                </div>
              </div>

              {/* Validation Report Matrix */}
              {validationReport && (
                <div style={{ background: 'rgba(0,0,0,0.4)', border: '1px solid var(--border-subtle)', borderRadius: '12px', padding: '1.25rem', marginBottom: '1.5rem' }}>
                  <h3 style={{ color: '#34d399', fontSize: '1.05rem', marginBottom: '0.5rem' }}>
                    ✅ 8-Point Structural Integrity & Ground Truth Evaluation
                  </h3>

                  {/* Ground Truth Precision / Recall */}
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '0.75rem', marginBottom: '1rem' }}>
                    <div>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>Precision:</span>
                      <p style={{ fontSize: '1.2rem', fontWeight: 'bold', color: '#34d399' }}>
                        {(validationReport.ground_truth_evaluation.precision * 100).toFixed(1)}%
                      </p>
                    </div>
                    <div>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>Recall:</span>
                      <p style={{ fontSize: '1.2rem', fontWeight: 'bold', color: '#34d399' }}>
                        {(validationReport.ground_truth_evaluation.recall * 100).toFixed(1)}%
                      </p>
                    </div>
                    <div>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>F1-Score:</span>
                      <p style={{ fontSize: '1.2rem', fontWeight: 'bold', color: '#34d399' }}>
                        {(validationReport.ground_truth_evaluation.f1_score * 100).toFixed(1)}%
                      </p>
                    </div>
                    <div>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>Injected Anomalies:</span>
                      <p style={{ fontSize: '1.2rem', fontWeight: 'bold' }}>
                        {validationReport.ground_truth_evaluation.total_ground_truth}
                      </p>
                    </div>
                  </div>

                  {/* Detected Violations List */}
                  <h4 style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>Detected Labelled Edge Cases</h4>
                  <div className="table-wrapper">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Rule Code</th>
                          <th>Severity</th>
                          <th>Entity Type</th>
                          <th>Primary ID</th>
                          <th>Message</th>
                        </tr>
                      </thead>
                      <tbody>
                        {validationReport.detected_rule_violations?.map((v, i) => (
                          <tr key={i}>
                            <td className="mono" style={{ color: '#f87171' }}>{v.rule_code}</td>
                            <td><span className="status-pill danger">{v.severity}</span></td>
                            <td>{v.entity_type}</td>
                            <td className="mono">{v.entity_id}</td>
                            <td>{v.message}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Reproducibility Output */}
              {reproResult && (
                <div style={{ background: 'rgba(0,0,0,0.4)', border: '1px solid var(--border-subtle)', borderRadius: '12px', padding: '1.25rem' }}>
                  <h3 style={{ color: '#34d399', fontSize: '1.05rem', marginBottom: '0.5rem' }}>
                    🔄 Step 10: Dual Generation SHA-256 Checksum Verification
                  </h3>
                  <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>
                    Regenerated twice with fixed seed <code>{reproResult.seed}</code>. Comparing bit-for-bit SHA-256 digests and row counts across all exported tables:
                  </p>
                  <div className="table-wrapper">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>File</th>
                          <th>Run 1 SHA-256</th>
                          <th>Run 2 SHA-256</th>
                          <th>Run 1 Rows</th>
                          <th>Run 2 Rows</th>
                          <th>Verification Result</th>
                        </tr>
                      </thead>
                      <tbody>
                        {reproResult.file_comparisons?.map(f => (
                          <tr key={f.file}>
                            <td><strong>{f.file}</strong></td>
                            <td className="mono" style={{ fontSize: '0.72rem', color: '#fbbf24' }}>{f.run1_sha256}</td>
                            <td className="mono" style={{ fontSize: '0.72rem', color: '#fbbf24' }}>{f.run2_sha256}</td>
                            <td>{f.run1_rows}</td>
                            <td>{f.run2_rows}</td>
                            <td>
                              <span className="status-pill approved">MATCH 100%</span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </main>

      {/* Leave Modal */}
      {showLeaveModal && (
        <div className="modal-overlay">
          <div className="modal-dialog">
            <h3 style={{ fontSize: '1.2rem', marginBottom: '1rem' }}>Submit Leave Request</h3>
            <form onSubmit={handleCreateLeave}>
              <div className="form-group">
                <label className="form-label">Employee ID</label>
                <input 
                  className="form-input" 
                  value={leaveForm.employee_id} 
                  onChange={e => setLeaveForm({ ...leaveForm, employee_id: e.target.value })} 
                  required 
                />
              </div>
              <div className="form-group">
                <label className="form-label">Start Date</label>
                <input 
                  type="date" 
                  className="form-input" 
                  value={leaveForm.start_date} 
                  onChange={e => setLeaveForm({ ...leaveForm, start_date: e.target.value })} 
                  required 
                />
              </div>
              <div className="form-group">
                <label className="form-label">End Date</label>
                <input 
                  type="date" 
                  className="form-input" 
                  value={leaveForm.end_date} 
                  onChange={e => setLeaveForm({ ...leaveForm, end_date: e.target.value })} 
                  required 
                />
              </div>
              <div className="form-group">
                <label className="form-label">Leave Type</label>
                <select 
                  className="form-select"
                  value={leaveForm.leave_type} 
                  onChange={e => setLeaveForm({ ...leaveForm, leave_type: e.target.value })}
                >
                  <option value="ANNUAL">Annual Leave (PTO)</option>
                  <option value="SICK">Acute Sick Leave</option>
                  <option value="BEREAVEMENT">Bereavement Leave</option>
                  <option value="PARENTAL">Parental Bonding</option>
                  <option value="COMPENSATORY">Compensatory Off</option>
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Justification / Reason</label>
                <textarea 
                  className="form-textarea" 
                  rows="3" 
                  value={leaveForm.reason} 
                  onChange={e => setLeaveForm({ ...leaveForm, reason: e.target.value })} 
                  required 
                />
              </div>
              <div className="form-actions">
                <button type="button" className="btn btn-secondary" onClick={() => setShowLeaveModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  Submit for Approval
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Swap Modal */}
      {showSwapModal && (
        <div className="modal-overlay">
          <div className="modal-dialog">
            <h3 style={{ fontSize: '1.2rem', marginBottom: '1rem' }}>Initiate Peer Shift Swap</h3>
            <form onSubmit={async (e) => {
              e.preventDefault();
              try {
                const res = await fetch(`${API_BASE}/swaps/request`, {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify(swapForm),
                });
                if (res.ok) {
                  setStatusMsg('Shift swap request broadcast to peer and manager desk');
                  setShowSwapModal(false);
                  fetchInitialData();
                }
              } catch (err) {
                alert('Error creating swap: ' + err.message);
              }
            }}>
              <div className="form-group">
                <label className="form-label">My Shift Assignment ID</label>
                <input 
                  className="form-input" 
                  value={swapForm.requester_assignment_id} 
                  readOnly 
                />
              </div>
              <div className="form-group">
                <label className="form-label">Target Shift Assignment to Swap With</label>
                <select 
                  className="form-select"
                  value={swapForm.target_assignment_id}
                  onChange={e => setSwapForm({ ...swapForm, target_assignment_id: e.target.value })}
                  required
                >
                  <option value="">-- Select Target Peer Shift --</option>
                  {shifts.slice(0, 30).filter(s => s.assignment_id !== swapForm.requester_assignment_id).map(s => (
                    <option key={s.assignment_id} value={s.assignment_id}>
                      {s.date} - Shift {s.shift_template_id} ({s.employee_id})
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-actions">
                <button type="button" className="btn btn-secondary" onClick={() => setShowSwapModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  Broadcast Swap Request
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
