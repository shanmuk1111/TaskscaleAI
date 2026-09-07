import { useEffect, useState } from "react";

function App() {
  const [stats, setStats] = useState({
    total_jobs: 0,
    queued_jobs: 0,
    running_jobs: 0,
    completed_jobs: 0,
    failed_jobs: 0,
  });

  const [workerStats, setWorkerStats] = useState({
    total_workers: 0,
    alive_workers: 0,
    dead_workers: 0,
  });

  const [recentJobs, setRecentJobs] = useState([]);

  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([
      fetch("http://127.0.0.1:8000/jobs/stats"),
      fetch("http://127.0.0.1:8000/workers/stats"),
      fetch("http://127.0.0.1:8000/jobs/recent"),
    ])
      .then(async ([jobsResponse, workersResponse, recentResponse]) => {
        if (
          !jobsResponse.ok ||
          !workersResponse.ok ||
          !recentResponse.ok
        ) {
          throw new Error("Failed to fetch dashboard data");
        }

        const jobsData = await jobsResponse.json();
        const workersData = await workersResponse.json();
        const recentData = await recentResponse.json();

        return {
          jobsData,
          workersData,
          recentData,
        };
      })
      .then(({ jobsData, workersData, recentData }) => {
        setStats(jobsData);
        setWorkerStats(workersData);
        setRecentJobs(recentData);
      })
      .catch((err) => {
        setError(err.message);
      });
  }, []);

  return (
    <div className="dashboard">
      <header className="header">
        <h1>TaskScale AI</h1>
        <p>Distributed Job Execution Dashboard</p>
      </header>

      <main>
        {error && (
          <div className="error">
            {error}
          </div>
        )}

        <section className="stats-grid">
          <div className="card">
            <h3>Total Jobs</h3>
            <p>{stats.total_jobs}</p>
          </div>

          <div className="card">
            <h3>Queued</h3>
            <p>{stats.queued_jobs}</p>
          </div>

          <div className="card">
            <h3>Running</h3>
            <p>{stats.running_jobs}</p>
          </div>

          <div className="card">
            <h3>Completed</h3>
            <p>{stats.completed_jobs}</p>
          </div>

          <div className="card">
            <h3>Failed</h3>
            <p>{stats.failed_jobs}</p>
          </div>

          <div className="card">
            <h3>Workers</h3>
            <p>{workerStats.alive_workers}</p>
          </div>
        </section>

        <section className="section">
          <h2>System Status</h2>

          <div className="status-card">
            <p>
              <strong>Backend:</strong> Connected
            </p>

            <p>
              <strong>Queue:</strong> Redis
            </p>

            <p>
              <strong>Database:</strong> PostgreSQL
            </p>
          </div>
        </section>

        <section className="section">
          <h2>Recent Jobs</h2>

          <div className="jobs-table">
            {recentJobs.length === 0 ? (
              <p>No jobs found.</p>
            ) : (
              <table>
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Type</th>
                    <th>Status</th>
                    <th>Priority</th>
                    <th>Retry Count</th>
                    <th>Worker</th>
                    <th>Created At</th>
                  </tr>
                </thead>

                <tbody>
                  {recentJobs.map((job) => (
                    <tr key={job.id}>
                      <td>{job.id}</td>
                      <td>{job.type}</td>
                      <td>{job.status}</td>
                      <td>{job.priority}</td>
                      <td>{job.retry_count}</td>
                      <td>{job.worker_id || "-"}</td>
                      <td>
                        {new Date(job.created_at).toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </section>
      </main>
    </div>
  );
}

export default App;