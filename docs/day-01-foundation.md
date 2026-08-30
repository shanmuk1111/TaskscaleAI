# Day 1 — TaskScale AI Foundation

## What is TaskScale AI?

TaskScale AI is a distributed job execution platform.
It accepts jobs, manages them, distributes them to workers,
tracks their execution, and eventually handles failures and recovery.

## Core Concepts

### Job
A task that needs to be executed.

Examples:
- Image resizing
- Sending an email
- PDF generation

### Worker
A program that executes a job.

### Queue
A place where jobs wait until workers can process them.

### Scheduler
A component that decides/manages which jobs should be processed.

### Workflow
A sequence of jobs that depend on each other.

Example:

Upload file
↓
Extract text
↓
Run AI
↓
Generate report

## Basic Job Flow

User
↓
API
↓
Job
↓
Queue
↓
Worker
↓
Result

## Important Failure Questions

- What happens if a worker crashes?
- What happens if two workers receive the same job?
- What happens if Redis fails?
- What happens if PostgreSQL fails?
- How do we recover unfinished jobs?