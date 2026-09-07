import React, { useEffect, useState } from "react";

import {
  ReactFlow,
  Background,
  Controls,
  MiniMap
} from "@xyflow/react";

import "@xyflow/react/dist/style.css";



function WorkflowOverview({ workflow }) {
  return (
    <div
      style={{
        position: "absolute",
        right: "15px",
        bottom: "15px",
        width: "180px",
        height: "100px",
        background: "#ffffff",
        border: "1px solid #cbd5e1",
        borderRadius: "10px",
        boxShadow: "0 4px 12px rgba(0,0,0,0.12)",
        zIndex: 10,
        padding: "10px",
      }}
    >
      <div
        style={{
          fontSize: "11px",
          fontWeight: "700",
          color: "#475569",
          marginBottom: "8px",
        }}
      >
        Workflow Overview
      </div>

      <div
        style={{
          position: "relative",
          height: "65px",
        }}
      >
        {workflow.map((job, index) => {
          let background = "#94a3b8";

          if (job.status === "COMPLETED") {
            background = "#22c55e";
          } else if (job.status === "FAILED") {
            background = "#ef4444";
          } else if (job.status === "RUNNING") {
            background = "#a855f7";
          } else if (job.status === "QUEUED") {
            background = "#eab308";
          }

          return (
            <div
              key={job.id}
              title={`Job #${job.id} - ${job.status}`}
              style={{
                position: "absolute",
                left: `${20 + index * 48}px`,
                top: "22px",
                width: "28px",
                height: "18px",
                borderRadius: "4px",
                background,
                border: "1px solid #64748b",
              }}
            />
          );
        })}

        {workflow.length > 1 &&
          workflow.slice(0, -1).map((job, index) => (
            <div
              key={`line-${job.id}`}
              style={{
                position: "absolute",
                left: `${48 + index * 48}px`,
                top: "30px",
                width: "20px",
                height: "2px",
                background: "#94a3b8",
              }}
            />
          ))}
      </div>
    </div>
  );
}

function buildWorkflowGroups(jobs) {
  if (!jobs || jobs.length === 0) {
    return [];
  }

  const jobMap = new Map(
    jobs.map((job) => [job.id, job])
  );

  // Build connections between jobs
  const graph = new Map();

  jobs.forEach((job) => {
    graph.set(job.id, new Set());
  });

  jobs.forEach((job) => {
    const dependencies = [
      ...(job.dependencies || []),
      ...(job.depends_on ? [job.depends_on] : [])
    ];

    dependencies.forEach((dependencyId) => {
      if (jobMap.has(dependencyId)) {
        // Connect both directions.
        // This helps us find the complete workflow.
        graph.get(job.id).add(dependencyId);
        graph.get(dependencyId).add(job.id);
      }
    });
  });

  // Find connected workflow groups
  const visited = new Set();
  const groups = [];

  jobs.forEach((job) => {
    if (visited.has(job.id)) {
      return;
    }

    const group = [];
    const queue = [job.id];

    visited.add(job.id);

    while (queue.length > 0) {
      const currentId = queue.shift();

      group.push(jobMap.get(currentId));

      graph.get(currentId).forEach((connectedId) => {
        if (!visited.has(connectedId)) {
          visited.add(connectedId);
          queue.push(connectedId);
        }
      });
    }

    // Only keep groups that actually contain dependencies
    const hasDependency = group.some(
      (job) =>
        (job.dependencies &&
          job.dependencies.length > 0) ||
        job.depends_on
    );

    if (hasDependency) {
      groups.push(group);
    }
  });

  // Latest workflow first
  groups.sort((a, b) => {
    const maxA = Math.max(...a.map((job) => job.id));
    const maxB = Math.max(...b.map((job) => job.id));

    return maxB - maxA;
  });

  return groups;
}



function buildFlowData(workflow) {
  const nodes = workflow.map((job, index) => ({
    id: String(job.id),

    position: {
      x: 100 + (index % 3) * 280,
      y: Math.floor(index / 3) * 180
    },

    data: {
      status: job.status,
      label: (
        <div>
          <div
            style={{
              fontSize: "12px",
              color: "#64748b",
              marginBottom: "8px"
            }}
          >
            JOB #{job.id}
          </div>

          <div
            style={{
              fontWeight: "700",
              fontSize: "15px",
              marginBottom: "10px"
            }}
          >
            {job.type}
          </div>

          <span
            className={`status-badge ${job.status.toLowerCase()}`}
          >
            {job.status}
          </span>

          <div
            style={{
              marginTop: "10px",
              fontSize: "12px",
              color: "#64748b"
            }}
          >
            Priority: {job.priority}
          </div>
        </div>
      )
    },

    style: {
      width: 210,
      padding: 15,
      borderRadius: 14,
      border: "1px solid #dbe3f0",
      background: "#ffffff",
      boxShadow: "0 5px 15px rgba(0,0,0,0.07)"
    }
  }));


  const edges = [];

  workflow.forEach((job) => {

    const dependencies = [
      ...(job.dependencies || []),
      ...(job.depends_on ? [job.depends_on] : [])
    ];

    dependencies.forEach((dependencyId) => {

      if (
        workflow.some(
          (item) => item.id === dependencyId
        )
      ) {

        edges.push({
          id: `${dependencyId}-${job.id}`,

          source: String(dependencyId),

          target: String(job.id),

          animated: job.status === "RUNNING",

          style: {
            strokeWidth: 2
          }
        });

      }

    });

  });


  return {
    nodes,
    edges
  };
}




function App() {
  // ================================
  // PAGE
  // ================================

  const [activePage, setActivePage] = useState("dashboard");

  // ================================
  // DASHBOARD DATA
  // ================================

  const [stats, setStats] = useState({
    total_jobs: 0,
    queued_jobs: 0,
    running_jobs: 0,
    completed_jobs: 0,
    failed_jobs: 0,
    queue_size: 0,
    success_rate: 0,
    average_latency_seconds: 0,
    total_retries: 0,
    worker_utilization: 0,
  });

  const [workerStats, setWorkerStats] = useState({
    total_workers: 0,
    alive_workers: 0,
    dead_workers: 0,
  });

  const [workflows, setWorkflows] = useState([]);

  const [workers, setWorkers] = useState([]);
  const [recentJobs, setRecentJobs] = useState([]);

  // ================================
  // JOBS PAGE
  // ================================

  const [jobs, setJobs] = useState([]);
  const [jobTotal, setJobTotal] = useState(0);
  const [jobPage, setJobPage] = useState(1);
  const [jobTotalPages, setJobTotalPages] = useState(0);
  const [jobSearch, setJobSearch] = useState("");
  const [jobStatus, setJobStatus] = useState("");

  // ================================
  // WORKERS PAGE
  // ================================

  const [workerFilter, setWorkerFilter] = useState("all");

  // ================================
  // QUEUE PAGE
  // ================================

  const [queueJobs, setQueueJobs] = useState([]);
  const [queueSize, setQueueSize] = useState(0);

  // ================================
  // GENERAL
  // ================================

  const [error, setError] = useState("");
  const [lastUpdated, setLastUpdated] = useState(null);

  // ================================
  // FETCH DASHBOARD DATA
  // ================================

  const fetchWorkflows = async () => {
    try {
      const response = await fetch(
        `http://127.0.0.1:8000/workflows?refresh=${Date.now()}`,
        {
          cache: "no-store",
        }
      );

      if (!response.ok) {
        throw new Error(
          `Workflow API error: ${response.status}`
        );
      }

      const data = await response.json();

      if (!Array.isArray(data)) {
        throw new Error(
          "Workflow API returned invalid data"
        );
      }

      console.log("Workflow refresh:", data);

      // Do not erase valid workflow data if
      // the backend temporarily returns an empty list.
      if (data.length > 0) {
        setWorkflows(data);
      }

    } catch (error) {
      console.error(
        "Failed to fetch workflows:",
        error
      );
    }
  };



  const fetchDashboardData = async () => {
    try {
      const [
        jobsResponse,
        workersResponse,
        recentJobsResponse,
        workersDetailsResponse,
      ] = await Promise.all([
        fetch("http://127.0.0.1:8000/jobs/stats"),
        fetch("http://127.0.0.1:8000/workers/stats"),
        fetch("http://127.0.0.1:8000/jobs/recent"),
        fetch("http://127.0.0.1:8000/workers"),
      ]);

      if (
        !jobsResponse.ok ||
        !workersResponse.ok ||
        !recentJobsResponse.ok ||
        !workersDetailsResponse.ok
      ) {
        throw new Error("Failed to fetch dashboard data");
      }

      const jobsData = await jobsResponse.json();
      const workersData = await workersResponse.json();
      const recentJobsData = await recentJobsResponse.json();
      const workersDetailsData =
        await workersDetailsResponse.json();

      setStats(jobsData);
      setWorkerStats(workersData);
      setRecentJobs(recentJobsData);
      setWorkers(workersDetailsData.workers);

      setError("");
      setLastUpdated(new Date());
    } catch (err) {
      setError(err.message);
    }
  };

  // ================================
  // FETCH ALL JOBS
  // ================================

  const fetchJobs = async () => {
    try {
      const params = new URLSearchParams();

      params.append("page", jobPage);
      params.append("limit", 20);

      if (jobSearch.trim()) {
        params.append("search", jobSearch.trim());
      }

      if (jobStatus) {
        params.append("status", jobStatus);
      }

      const response = await fetch(
        `http://127.0.0.1:8000/jobs?${params.toString()}`
      );

      if (!response.ok) {
        throw new Error("Failed to fetch jobs");
      }

      const data = await response.json();

      setJobs(data.jobs);
      setJobTotal(data.total);
      setJobTotalPages(data.total_pages);
    } catch (err) {
      setError(err.message);
    }
  };

  // ================================
  // FETCH QUEUE
  // ================================

  const fetchQueue = async () => {
    try {
      const response = await fetch(
        "http://127.0.0.1:8000/queue"
      );

      if (!response.ok) {
        throw new Error("Failed to fetch queue");
      }

      const data = await response.json();

      setQueueSize(data.queue_size);
      setQueueJobs(data.jobs);
    } catch (err) {
      setError(err.message);
    }
  };

  // ================================
  // AUTO REFRESH
  // ================================

  useEffect(() => {
    fetchDashboardData();
    fetchJobs();
    fetchQueue();
    fetchWorkflows();

    const interval = setInterval(() => {
      fetchDashboardData();
      fetchJobs();
      fetchQueue();
      fetchWorkflows();
    }, 5000);

    return () => {
      clearInterval(interval);
    };
  }, [jobPage, jobSearch, jobStatus]);

  // ================================
  // HELPERS
  // ================================

  const getStatusClass = (status) => {
    return status ? status.toLowerCase() : "";
  };

  const formatTime = (date) => {
    if (!date) return "-";

    return new Date(date).toLocaleString();
  };

  // ================================
  // RECENT WORKERS
  // ================================

  const recentWorkers = [...workers]
    .sort(
      (a, b) =>
        new Date(b.last_heartbeat) -
        new Date(a.last_heartbeat)
    )
    .slice(0, 3);

  // ================================
  // FILTERED WORKERS
  // ================================

  const filteredWorkers = [...workers]
    .filter((worker) => {
      if (workerFilter === "alive") {
        return worker.status === "ALIVE";
      }

      if (workerFilter === "dead") {
        return worker.status === "DEAD";
      }

      return true;
    })
    .sort((a, b) => {
      // Alive workers first
      if (a.status === "ALIVE" && b.status !== "ALIVE") {
        return -1;
      }

      if (a.status !== "ALIVE" && b.status === "ALIVE") {
        return 1;
      }

      // Then latest heartbeat
      return (
        new Date(b.last_heartbeat) -
        new Date(a.last_heartbeat)
      );
    });

  // ================================
  // JOB HANDLERS
  // ================================

  const handleSearchChange = (event) => {
    setJobSearch(event.target.value);
    setJobPage(1);
  };

  const handleStatusChange = (event) => {
    setJobStatus(event.target.value);
    setJobPage(1);
  };

  const previousPage = () => {
    if (jobPage > 1) {
      setJobPage(jobPage - 1);
    }
  };

  const nextPage = () => {
    if (jobPage < jobTotalPages) {
      setJobPage(jobPage + 1);
    }
  };

  // ================================
  // NAVIGATION
  // ================================

  const showDashboard = () => {
    setActivePage("dashboard");

    window.scrollTo({
      top: 0,
      behavior: "smooth",
    });
  };

  const showJobs = () => {
    setActivePage("jobs");

    window.scrollTo({
      top: 0,
      behavior: "smooth",
    });
  };

  const showWorkers = () => {
    setActivePage("workers");

    window.scrollTo({
      top: 0,
      behavior: "smooth",
    });
  };

  const showQueue = () => {
    setActivePage("queue");

    window.scrollTo({
      top: 0,
      behavior: "smooth",
    });
  };

  // ================================
  // RENDER
  // ================================

  return (
    <div className="app-shell">

      {/* =================================
          SIDEBAR
      ================================= */}

      <aside className="sidebar">

        <div className="brand">

          <div className="brand-icon">
            TS
          </div>

          <div>
            <h1>
              TaskScale <span>AI</span>
            </h1>

            <p>
              Distributed Job Execution
            </p>
          </div>

        </div>

        <nav className="sidebar-nav">

          {/* DASHBOARD */}

          <div
            className={`nav-item ${activePage === "dashboard"
              ? "active"
              : ""
              }`}
            onClick={showDashboard}
          >
            <span>⌂</span>
            Dashboard
          </div>

          {/* JOBS */}

          <div
            className={`nav-item ${activePage === "jobs"
              ? "active"
              : ""
              }`}
            onClick={showJobs}
          >
            <span>☷</span>
            Jobs
          </div>

          {/* WORKERS */}

          <div
            className={`nav-item ${activePage === "workers"
              ? "active"
              : ""
              }`}
            onClick={showWorkers}
          >
            <span>♟</span>
            Workers
          </div>

          {/* WORKFLOWS */}

          <div
            className={`nav-item ${activePage === "workflows" ? "active" : ""
              }`}
            onClick={() => setActivePage("workflows")}
          >
            <span>◇</span>
            Workflows
          </div>

          {/* QUEUE */}

          <div
            className={`nav-item ${activePage === "queue"
              ? "active"
              : ""
              }`}
            onClick={showQueue}
          >
            <span>▤</span>
            Queue
          </div>

          {/* ANALYTICS */}

          <div
            className="nav-item"
            onClick={() =>
              alert(
                "Analytics page will be added later."
              )
            }
          >
            <span>▥</span>
            Analytics
          </div>

          {/* SETTINGS */}

          <div
            className="nav-item"
            onClick={() =>
              alert(
                "Settings page will be added later."
              )
            }
          >
            <span>⚙</span>
            Settings
          </div>

        </nav>

        <div className="sidebar-bottom">

          <div className="online-card">

            <div className="online-title">
              <span className="online-dot"></span>
              System Online
            </div>

            <p>
              All services running
            </p>

          </div>

        </div>

      </aside>

      {/* =================================
          MAIN CONTENT
      ================================= */}

      <main className="main-content">

        {/* HEADER */}

        <header className="top-header">

          <div>

            <h2>
              {activePage === "dashboard" &&
                "Welcome back!"}

              {activePage === "jobs" &&
                "Job Monitoring"}

              {activePage === "workers" &&
                "Worker Monitoring"}

              {activePage === "queue" &&
                "Queue Monitoring"}
            </h2>

            <p>
              {activePage === "dashboard" &&
                "Here's what's happening with your jobs today."}

              {activePage === "jobs" &&
                "Search, filter and monitor all TaskScale jobs."}

              {activePage === "workers" &&
                "Monitor worker health, heartbeat and workload."}

              {activePage === "queue" &&
                "Monitor waiting jobs and Redis priority queue activity."}
            </p>

          </div>

          <div className="header-right">

            <div className="live-status">

              <span className="live-dot"></span>

              <div>

                <strong>
                  Live Updates
                </strong>

                <small>
                  Last updated:{" "}
                  {lastUpdated
                    ? lastUpdated.toLocaleTimeString()
                    : "Loading..."}
                </small>

              </div>

            </div>

            <button
              className="refresh-icon"
              onClick={() => {
                fetchDashboardData();
                fetchJobs();
                fetchQueue();
                fetchWorkflows();
              }}
              title="Refresh dashboard"
            >
              ↻
            </button>

          </div>

        </header>

        {/* ERROR */}

        {error && (
          <div className="error">
            <strong>
              Connection Error:
            </strong>{" "}
            {error}
          </div>
        )}

        {/* =================================
            DASHBOARD PAGE
        ================================= */}

        {activePage === "dashboard" && (

          <>

            {/* PRIMARY METRICS */}

            <section className="metrics-grid">

              <div className="metric-card blue">
                <div className="metric-icon">
                  ▤
                </div>

                <div className="metric-content">
                  <span>Total Jobs</span>

                  <strong>
                    {stats.total_jobs}
                  </strong>
                </div>
              </div>

              <div className="metric-card yellow">

                <div className="metric-icon">
                  ◷
                </div>

                <div className="metric-content">
                  <span>Queued</span>

                  <strong>
                    {stats.queued_jobs}
                  </strong>
                </div>

              </div>

              <div className="metric-card purple">

                <div className="metric-icon">
                  ⚙
                </div>

                <div className="metric-content">
                  <span>Running</span>

                  <strong>
                    {stats.running_jobs}
                  </strong>
                </div>

              </div>

              <div className="metric-card green">

                <div className="metric-icon">
                  ✓
                </div>

                <div className="metric-content">
                  <span>Completed</span>

                  <strong>
                    {stats.completed_jobs}
                  </strong>
                </div>

              </div>

              <div className="metric-card red">

                <div className="metric-icon">
                  ×
                </div>

                <div className="metric-content">
                  <span>Failed</span>

                  <strong>
                    {stats.failed_jobs}
                  </strong>
                </div>

              </div>

            </section>

            {/* SECONDARY METRICS */}

            <section className="secondary-grid">

              <div className="small-card blue">

                <div className="small-card-icon">
                  ♟
                </div>

                <div>

                  <span>
                    Workers Online
                  </span>

                  <strong>
                    {workerStats.alive_workers} /{" "}
                    {workerStats.total_workers}
                  </strong>

                  <small>
                    {workerStats.dead_workers} dead
                  </small>

                </div>

              </div>

              <div className="small-card purple">

                <div className="small-card-icon">
                  ▤
                </div>

                <div>

                  <span>
                    Queue Size
                  </span>

                  <strong>
                    {stats.queue_size}
                  </strong>

                  <small>
                    Waiting jobs
                  </small>

                </div>

              </div>

              <div className="small-card green">

                <div className="small-card-icon">
                  ◎
                </div>

                <div>

                  <span>
                    Success Rate
                  </span>

                  <strong>
                    {stats.success_rate}%
                  </strong>

                  <small>
                    Completed / Finished
                  </small>

                </div>

              </div>

              <div className="small-card yellow">

                <div className="small-card-icon">
                  ϟ
                </div>

                <div>

                  <span>
                    Avg Latency
                  </span>

                  <strong>
                    {stats.average_latency_seconds}s
                  </strong>

                  <small>
                    Job latency
                  </small>

                </div>

              </div>

              <div className="small-card blue">

                <div className="small-card-icon">
                  ↻
                </div>

                <div>

                  <span>
                    Total Retries
                  </span>

                  <strong>
                    {stats.total_retries}
                  </strong>

                  <small>
                    Retry attempts
                  </small>

                </div>

              </div>

              <div className="small-card pink">

                <div className="small-card-icon">
                  ▥
                </div>

                <div>

                  <span>
                    Worker Utilization
                  </span>

                  <strong>
                    {stats.worker_utilization}%
                  </strong>

                  <small>
                    Current utilization
                  </small>

                </div>

              </div>

            </section>

            {/* MONITORING */}

            <section className="monitoring-grid">

              {/* JOB DISTRIBUTION */}

              <div className="panel">

                <div className="panel-header">

                  <div>

                    <h3>
                      Job Status Distribution
                    </h3>

                    <p>
                      Current workload breakdown
                    </p>

                  </div>

                </div>

                <div className="distribution">

                  <div className="distribution-total">

                    <strong>
                      {stats.total_jobs}
                    </strong>

                    <span>
                      Total Jobs
                    </span>

                  </div>

                  <div className="distribution-list">

                    <div className="distribution-item">

                      <div className="distribution-label">

                        <span className="legend completed"></span>

                        Completed

                      </div>

                      <strong>
                        {stats.completed_jobs}
                      </strong>

                    </div>

                    <div className="progress">

                      <div
                        className="progress completed"
                        style={{
                          width: `${stats.total_jobs
                            ? (stats.completed_jobs /
                              stats.total_jobs) *
                            100
                            : 0
                            }%`,
                        }}
                      ></div>

                    </div>

                    <div className="distribution-item">

                      <div className="distribution-label">

                        <span className="legend running"></span>

                        Running

                      </div>

                      <strong>
                        {stats.running_jobs}
                      </strong>

                    </div>

                    <div className="progress">

                      <div
                        className="progress running"
                        style={{
                          width: `${stats.total_jobs
                            ? (stats.running_jobs /
                              stats.total_jobs) *
                            100
                            : 0
                            }%`,
                        }}
                      ></div>

                    </div>

                    <div className="distribution-item">

                      <div className="distribution-label">

                        <span className="legend queued"></span>

                        Queued

                      </div>

                      <strong>
                        {stats.queued_jobs}
                      </strong>

                    </div>

                    <div className="progress">

                      <div
                        className="progress queued"
                        style={{
                          width: `${stats.total_jobs
                            ? (stats.queued_jobs /
                              stats.total_jobs) *
                            100
                            : 0
                            }%`,
                        }}
                      ></div>

                    </div>

                    <div className="distribution-item">

                      <div className="distribution-label">

                        <span className="legend failed"></span>

                        Failed

                      </div>

                      <strong>
                        {stats.failed_jobs}
                      </strong>

                    </div>

                    <div className="progress">

                      <div
                        className="progress failed"
                        style={{
                          width: `${stats.total_jobs
                            ? (stats.failed_jobs /
                              stats.total_jobs) *
                            100
                            : 0
                            }%`,
                        }}
                      ></div>

                    </div>

                  </div>

                </div>

              </div>

              {/* SYSTEM STATUS */}

              <div className="panel system-panel">

                <div className="panel-header">

                  <div>

                    <h3>
                      System Status
                    </h3>

                    <p>
                      Infrastructure health
                    </p>

                  </div>

                  <span className="healthy-badge">
                    ✓ Healthy
                  </span>

                </div>

                <div className="service-list">

                  <div className="service">

                    <div className="service-name">

                      <span className="service-icon">
                        ◆
                      </span>

                      Backend

                    </div>

                    <span className="service-status">

                      <span></span>

                      Connected

                    </span>

                  </div>

                  <div className="service">

                    <div className="service-name">

                      <span className="service-icon">
                        ◆
                      </span>

                      Redis Queue

                    </div>

                    <span className="service-status">

                      <span></span>

                      Connected

                    </span>

                  </div>

                  <div className="service">

                    <div className="service-name">

                      <span className="service-icon">
                        ◆
                      </span>

                      PostgreSQL

                    </div>

                    <span className="service-status">

                      <span></span>

                      Connected

                    </span>

                  </div>

                </div>

              </div>

            </section>

            {/* RECENT WORKERS */}

            <section className="panel">

              <div className="panel-header">

                <div>

                  <h3>
                    Recent Workers
                  </h3>

                  <p>
                    Most recently active workers
                  </p>

                </div>

                <button
                  className="view-all-button"
                  onClick={showWorkers}
                >
                  View all workers →
                </button>

              </div>

              <div className="recent-worker-grid">

                {recentWorkers.length === 0 ? (

                  <p className="empty">
                    No workers registered.
                  </p>

                ) : (

                  recentWorkers.map(
                    (worker, index) => (

                      <div
                        className="recent-worker-card"
                        key={worker.worker_id}
                      >

                        <div className="recent-worker-top">

                          <div className="recent-worker-name">

                            <span
                              className={`worker-status-dot ${getStatusClass(
                                worker.status
                              )}`}
                            ></span>

                            <div>

                              <strong>
                                Worker {index + 1}
                              </strong>

                              <small>
                                {worker.worker_id}
                              </small>

                            </div>

                          </div>

                          <span
                            className={`worker-status-badge ${getStatusClass(
                              worker.status
                            )}`}
                          >
                            {worker.status}
                          </span>

                        </div>

                        <div className="recent-worker-heartbeat">

                          <span>
                            Last heartbeat
                          </span>

                          <strong>
                            {formatTime(
                              worker.last_heartbeat
                            )}
                          </strong>

                        </div>

                      </div>

                    )
                  )

                )}

              </div>

            </section>

            {/* RECENT JOBS */}

            <section className="panel recent-panel">

              <div className="panel-header">

                <div>

                  <h3>
                    Recent Jobs
                  </h3>

                  <p>
                    Latest 10 jobs
                  </p>

                </div>

                <button
                  className="view-all-button"
                  onClick={showJobs}
                >
                  View all jobs →
                </button>

              </div>

              <div className="table-container">

                {recentJobs.length === 0 ? (

                  <p className="empty">
                    No jobs found.
                  </p>

                ) : (

                  <table>

                    <thead>

                      <tr>

                        <th>ID</th>
                        <th>TYPE</th>
                        <th>STATUS</th>
                        <th>PRIORITY</th>
                        <th>WORKER</th>
                        <th>CREATED AT</th>

                      </tr>

                    </thead>

                    <tbody>

                      {recentJobs.map(
                        (job) => (

                          <tr key={job.id}>

                            <td>

                              <strong className="job-id">
                                #{job.id}
                              </strong>

                            </td>

                            <td>

                              <span className="job-type">
                                {job.type}
                              </span>

                            </td>

                            <td>

                              <span
                                className={`status-badge ${getStatusClass(
                                  job.status
                                )}`}
                              >
                                {job.status}
                              </span>

                            </td>

                            <td>

                              <span className="priority-badge">
                                {job.priority}
                              </span>

                            </td>

                            <td>

                              <span className="worker-id">
                                {job.worker_id || "-"}
                              </span>

                            </td>

                            <td>
                              {formatTime(
                                job.created_at
                              )}
                            </td>

                          </tr>

                        )
                      )}

                    </tbody>

                  </table>

                )}

              </div>

            </section>

          </>

        )}

        {/* =================================
            JOBS PAGE
        ================================= */}

        {activePage === "jobs" && (

          <section className="panel full-page-panel">

            <div className="panel-header">

              <div>

                <h3>
                  All Jobs
                </h3>

                <p>
                  Search and filter all TaskScale jobs
                </p>

              </div>

              <span className="live-table-badge">
                ● Live
              </span>

            </div>

            <div className="job-controls">

              <input
                type="text"
                placeholder="Search by job type..."
                value={jobSearch}
                onChange={handleSearchChange}
              />

              <select
                value={jobStatus}
                onChange={handleStatusChange}
              >

                <option value="">
                  All Statuses
                </option>

                <option value="QUEUED">
                  Queued
                </option>

                <option value="RUNNING">
                  Running
                </option>

                <option value="COMPLETED">
                  Completed
                </option>

                <option value="FAILED">
                  Failed
                </option>

              </select>

            </div>

            <div className="job-summary">
              Showing {jobs.length} of {jobTotal} jobs
            </div>

            <div className="table-container">

              {jobs.length === 0 ? (

                <p className="empty">
                  No jobs found.
                </p>

              ) : (

                <table>

                  <thead>

                    <tr>

                      <th>ID</th>
                      <th>TYPE</th>
                      <th>STATUS</th>
                      <th>PRIORITY</th>
                      <th>RETRIES</th>
                      <th>WORKER</th>
                      <th>CREATED AT</th>

                    </tr>

                  </thead>

                  <tbody>

                    {jobs.map((job) => (

                      <tr key={job.id}>

                        <td>

                          <strong className="job-id">
                            #{job.id}
                          </strong>

                        </td>

                        <td>

                          <span className="job-type">
                            {job.type}
                          </span>

                        </td>

                        <td>

                          <span
                            className={`status-badge ${getStatusClass(
                              job.status
                            )}`}
                          >
                            {job.status}
                          </span>

                        </td>

                        <td>

                          <span className="priority-badge">
                            {job.priority}
                          </span>

                        </td>

                        <td>
                          {job.retry_count}
                        </td>

                        <td>

                          <span className="worker-id">
                            {job.worker_id || "-"}
                          </span>

                        </td>

                        <td>
                          {formatTime(
                            job.created_at
                          )}
                        </td>

                      </tr>

                    ))}

                  </tbody>

                </table>

              )}

            </div>

            <div className="pagination">

              <button
                onClick={previousPage}
                disabled={jobPage === 1}
              >
                ← Previous
              </button>

              <span>
                Page {jobPage} of{" "}
                {jobTotalPages || 1}
              </span>

              <button
                onClick={nextPage}
                disabled={
                  jobPage >= jobTotalPages ||
                  jobTotalPages === 0
                }
              >
                Next →
              </button>

            </div>

          </section>

        )}


        {/* WORKFLOWS PAGE */}



        {/* WORKFLOWS PAGE */}

        {activePage === "workflows" && (
          <div className="page-content">

            {/* HEADER */}

            <div className="page-header">
              <div>
                <h1>Workflows</h1>
                <p>
                  View and monitor workflow dependency pipelines
                </p>
              </div>
            </div>


            {/* WORKFLOW STATISTICS */}

            <div className="stats-grid">

              <div className="stat-card">
                <div className="stat-label">
                  Workflow Jobs
                </div>

                <div className="stat-value">
                  {buildWorkflowGroups(workflows)
                    .flat()
                    .length}
                </div>
              </div>


              <div className="stat-card">
                <div className="stat-label">
                  Completed
                </div>

                <div className="stat-value">
                  {
                    buildWorkflowGroups(workflows)
                      .flat()
                      .filter(
                        (job) => job.status === "COMPLETED"
                      )
                      .length
                  }
                </div>
              </div>


              <div className="stat-card">
                <div className="stat-label">
                  Running
                </div>

                <div className="stat-value">
                  {
                    buildWorkflowGroups(workflows)
                      .flat()
                      .filter(
                        (job) => job.status === "RUNNING"
                      )
                      .length
                  }
                </div>
              </div>


              <div className="stat-card">
                <div className="stat-label">
                  Failed
                </div>

                <div className="stat-value">
                  {
                    buildWorkflowGroups(workflows)
                      .flat()
                      .filter(
                        (job) => job.status === "FAILED"
                      )
                      .length
                  }
                </div>
              </div>

            </div>


            {/* VISUAL WORKFLOW DAG */}

            <div className="content-card">

              <div className="card-header">

                <div>
                  <h2>Workflow DAG</h2>

                  <span>
                    Interactive dependency execution flow
                  </span>
                </div>

              </div>

              {buildWorkflowGroups(workflows).length === 0 ? (

                <div className="empty-state">
                  No workflow dependencies found.
                </div>

              ) : (

                buildWorkflowGroups(workflows).map(
                  (workflow, workflowIndex) => {

                    const flowData = buildFlowData(workflow);

                    return (
                      <div
                        key={workflowIndex}
                        style={{
                          height: "600px",
                          margin: "20px",
                          border: "1px solid #e2e8f0",
                          borderRadius: "14px",
                          overflow: "hidden",
                          background: "#f8fafc",
                          position: "relative",
                        }}
                      >

                        <div
                          style={{
                            padding: "15px 20px",
                            fontWeight: "700",
                            fontSize: "15px",
                            background: "#ffffff",
                            borderBottom: "1px solid #e2e8f0"
                          }}
                        >
                          Workflow #{workflowIndex + 1}
                        </div>

                        <ReactFlow
                          nodes={flowData.nodes}
                          edges={flowData.edges}
                          fitView
                          fitViewOptions={{
                            padding: 0.2,
                          }}
                        >
                          <Background />

                          <Controls />

                          <MiniMap
                            nodeColor={(node) => {
                              switch (node.data?.status) {
                                case "COMPLETED":
                                  return "#22c55e";

                                case "FAILED":
                                  return "#ef4444";

                                case "RUNNING":
                                  return "#a855f7";

                                case "QUEUED":
                                  return "#eab308";

                                default:
                                  return "#94a3b8";
                              }
                            }}
                            nodeStrokeColor="#334155"
                            nodeStrokeWidth={2}
                            maskColor="rgba(0, 0, 0, 0.08)"
                          />
                        </ReactFlow>
                      </div>
                    );

                  }
                )

              )}

            </div>

            {/* WORKFLOW JOBS */}

            <div
              className="content-card"
              style={{ marginTop: "24px" }}
            >

              <div className="card-header">

                <div>
                  <h2>Workflow Jobs</h2>

                  <span>
                    Jobs belonging to the latest workflow
                  </span>
                </div>

              </div>


              <div className="table-container">

                <table className="data-table">

                  <thead>
                    <tr>
                      <th>Job ID</th>
                      <th>Type</th>
                      <th>Status</th>
                      <th>Priority</th>
                      <th>Dependencies</th>
                      <th>Created</th>
                    </tr>
                  </thead>


                  <tbody>

                    {buildWorkflowGroups(workflows)
                      .flat()
                      .map((job) => (

                        <tr key={job.id}>

                          <td>
                            #{job.id}
                          </td>

                          <td>
                            <strong>
                              {job.type}
                            </strong>
                          </td>

                          <td>
                            <span
                              className={`status-badge ${job.status.toLowerCase()}`}
                            >
                              {job.status}
                            </span>
                          </td>

                          <td>
                            {job.priority}
                          </td>

                          <td>

                            {job.dependencies &&
                              job.dependencies.length > 0
                              ? job.dependencies.map(
                                (dependency) => (
                                  <span
                                    key={dependency}
                                    className="dependency-tag"
                                  >
                                    #{dependency}
                                  </span>
                                )
                              )
                              : job.depends_on
                                ? `#${job.depends_on}`
                                : "None"}

                          </td>

                          <td>
                            {job.created_at
                              ? new Date(
                                job.created_at
                              ).toLocaleString()
                              : "-"}
                          </td>

                        </tr>

                      ))}

                  </tbody>

                </table>

              </div>

            </div>

          </div>
        )}

        {/* =================================
            WORKERS PAGE
        ================================= */}

        {activePage === "workers" && (

          <section className="panel full-page-panel">

            <div className="panel-header">

              <div>

                <h3>
                  All Workers
                </h3>

                <p>
                  Monitor all registered workers
                </p>

              </div>

              <span className="live-table-badge">
                ● Live
              </span>

            </div>

            <div className="worker-summary-grid">

              <div className="worker-summary-card">

                <span>
                  Total Workers
                </span>

                <strong>
                  {workerStats.total_workers}
                </strong>

              </div>

              <div className="worker-summary-card alive-summary">

                <span>
                  Alive Workers
                </span>

                <strong>
                  {workerStats.alive_workers}
                </strong>

              </div>

              <div className="worker-summary-card dead-summary">

                <span>
                  Dead Workers
                </span>

                <strong>
                  {workerStats.dead_workers}
                </strong>

              </div>

            </div>

            <div className="worker-controls">

              <label>
                Worker Status
              </label>

              <select
                value={workerFilter}
                onChange={(event) =>
                  setWorkerFilter(
                    event.target.value
                  )
                }
              >

                <option value="all">
                  All Workers
                </option>

                <option value="alive">
                  Alive Workers
                </option>

                <option value="dead">
                  Dead Workers
                </option>

              </select>

            </div>

            <div className="full-worker-list">

              {filteredWorkers.length === 0 ? (

                <p className="empty">
                  No workers found.
                </p>

              ) : (

                filteredWorkers.map(
                  (worker, index) => (

                    <div
                      className={`full-worker-card ${getStatusClass(
                        worker.status
                      )}`}
                      key={worker.worker_id}
                    >

                      <div className="full-worker-header">

                        <div className="full-worker-name">

                          <span
                            className={`worker-status-dot ${getStatusClass(
                              worker.status
                            )}`}
                          ></span>

                          <div>

                            <strong>
                              Worker {index + 1}
                            </strong>

                            <small>
                              {worker.worker_id}
                            </small>

                          </div>

                        </div>

                        <span
                          className={`worker-status-badge ${getStatusClass(
                            worker.status
                          )}`}
                        >
                          {worker.status}
                        </span>

                      </div>

                      <div className="full-worker-details">

                        <div>

                          <span>
                            Last Heartbeat
                          </span>

                          <strong>
                            {formatTime(
                              worker.last_heartbeat
                            )}
                          </strong>

                        </div>

                        <div>

                          <span>
                            Running Jobs
                          </span>

                          <strong>
                            {worker.running_jobs}
                          </strong>

                        </div>

                        <div>

                          <span>
                            Completed Jobs
                          </span>

                          <strong>
                            {worker.completed_jobs}
                          </strong>

                        </div>

                        <div>

                          <span>
                            Failed Jobs
                          </span>

                          <strong>
                            {worker.failed_jobs}
                          </strong>

                        </div>

                      </div>

                    </div>

                  )
                )

              )}

            </div>

          </section>

        )}

        {/* =================================
            QUEUE PAGE
        ================================= */}

        {activePage === "queue" && (

          <section className="panel full-page-panel">

            <div className="panel-header">

              <div>

                <h3>
                  Queue Monitoring
                </h3>

                <p>
                  Monitor jobs waiting in the Redis priority queue
                </p>

              </div>

              <span className="live-table-badge">
                ● Live
              </span>

            </div>

            {/* QUEUE SUMMARY */}

            <div className="worker-summary-grid">

              <div className="worker-summary-card">

                <span>
                  Queue Size
                </span>

                <strong>
                  {queueSize}
                </strong>

              </div>

              <div className="worker-summary-card">

                <span>
                  Waiting Jobs
                </span>

                <strong>
                  {queueJobs.length}
                </strong>

              </div>

              <div className="worker-summary-card alive-summary">

                <span>
                  Redis Queue
                </span>

                <strong>
                  Connected
                </strong>

              </div>

            </div>

            {/* QUEUE INFORMATION */}

            <div
              style={{
                marginTop: "24px",
                marginBottom: "20px",
                padding: "18px",
                borderRadius: "14px",
                background: "#f8fafc",
                border: "1px solid #e5e7eb",
              }}
            >

              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "10px",
                  marginBottom: "6px",
                }}
              >

                <span
                  style={{
                    width: "10px",
                    height: "10px",
                    borderRadius: "50%",
                    background: "#22c55e",
                    display: "inline-block",
                  }}
                ></span>

                <strong>
                  Priority Queue Active
                </strong>

              </div>

              <p
                style={{
                  margin: 0,
                  color: "#64748b",
                  fontSize: "14px",
                }}
              >
                Jobs are ordered by priority before being processed
                by the scheduler and workers.
              </p>

            </div>

            {/* QUEUE TABLE */}

            <div className="table-container">

              {queueJobs.length === 0 ? (

                <div
                  style={{
                    textAlign: "center",
                    padding: "50px 20px",
                  }}
                >

                  <div
                    style={{
                      fontSize: "42px",
                      marginBottom: "12px",
                    }}
                  >
                    ✓
                  </div>

                  <h3
                    style={{
                      margin: "0 0 8px 0",
                    }}
                  >
                    Queue is empty
                  </h3>

                  <p
                    style={{
                      margin: 0,
                      color: "#64748b",
                    }}
                  >
                    There are no jobs waiting in the priority queue.
                  </p>

                </div>

              ) : (

                <table>

                  <thead>

                    <tr>

                      <th>ID</th>
                      <th>TYPE</th>
                      <th>STATUS</th>
                      <th>PRIORITY</th>
                      <th>RETRIES</th>
                      <th>CREATED AT</th>

                    </tr>

                  </thead>

                  <tbody>

                    {queueJobs.map((job) => (

                      <tr key={job.id}>

                        <td>

                          <strong className="job-id">
                            #{job.id}
                          </strong>

                        </td>

                        <td>

                          <span className="job-type">
                            {job.type}
                          </span>

                        </td>

                        <td>

                          <span
                            className={`status-badge ${getStatusClass(
                              job.status
                            )}`}
                          >
                            {job.status}
                          </span>

                        </td>

                        <td>

                          <span className="priority-badge">
                            {job.priority}
                          </span>

                        </td>

                        <td>
                          {job.retry_count}
                        </td>

                        <td>
                          {formatTime(
                            job.created_at
                          )}
                        </td>

                      </tr>

                    ))}

                  </tbody>

                </table>

              )}

            </div>

          </section>

        )}

      </main>

    </div>
  );
}

export default App;