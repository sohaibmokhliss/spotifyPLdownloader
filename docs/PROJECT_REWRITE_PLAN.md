# Project Rewrite Plan

This document is a project outline for rebuilding the current downloader into a more deployable product. It is not a description of what already exists in the current Flask prototype.

## 1. Project Goal

Build a new version of the app with:

- a public interface for anonymous users
- a `/vip` entry for the shared friends-and-family account
- a `/owner` entry for the owner account
- owner and VIP priority over public jobs
- a queue-driven download system instead of long-running in-memory Flask requests
- a deployment model that works with Vercel for the UI and a separate worker for heavy downloads

## 2. Target Product Shape

### User Tiers

- `public`
  - anonymous access
  - can submit downloads with strict limits
  - lowest priority
- `vip`
  - shared account for family and close friends
  - login route: `/vip`
  - higher priority than public
- `owner`
  - shared owner account
  - login route: `/owner`
  - highest priority
  - can access `/admin`

### Main Screens

- `/`
  - public landing page
  - downloader UI
  - status for anonymous jobs
- `/vip`
  - VIP sign-in
  - VIP dashboard with queue status and download access
- `/owner`
  - owner sign-in
  - owner dashboard
- `/admin`
  - owner-only operations page
  - queue visibility
  - logs
  - worker health
  - cancellation and reprioritization tools

## 3. Recommended Architecture

### Control Plane

Host the web app on Vercel.

Responsibilities:

- frontend pages
- auth and sessions
- job submission
- job listing and status polling
- admin pages

### Worker Plane

Run the actual download engine in a separate worker service.

Responsibilities:

- `yt-dlp`
- FFmpeg
- queue polling
- checkpoint updates
- archive creation
- cleanup

### Data and Storage

Use a real database and short-lived file storage.

Responsibilities:

- accounts and roles
- sessions
- jobs
- checkpoints
- logs
- output file metadata

## 4. Core Technical Principles

- Do not keep queue state in memory.
- Do not depend on a single long HTTP request to finish a download.
- Treat every download as a durable job with resumable state.
- Keep public traffic constrained with quotas and caps.
- Keep owner-only and VIP-only capabilities behind real session-based auth.
- Do not expose admin routes in the public UI.

## 5. Queue Model

### Priority Order

1. `owner`
2. `vip`
3. `public`

### Scheduling Rules

- Only one worker slot initially.
- Public jobs can run freely when no VIP or owner jobs are waiting.
- If a VIP or owner job arrives while a public job is active:
  - mark the public job for pause
  - pause at the next safe checkpoint
  - run the higher-priority job next
- Paused public jobs resume automatically when the privileged queue is empty.

### Public Limits

- 1 queued or running job per IP
- 5 jobs per day per IP
- 20-item playlist cap
- short file retention window

### VIP and Owner Limits

- VIP
  - 2 queued or running jobs
  - larger playlist cap
- Owner
  - 3 queued or running jobs
  - highest operational privilege

## 6. Data Model Outline

### Accounts

Create fixed privileged accounts:

- one `vip` account
- one `owner` account

Store:

- `id`
- `role`
- `username`
- `password_hash`
- `created_at`
- `last_login_at`
- `disabled`

### Jobs

Minimum fields:

- `id`
- `tier`
- `status`
- `source_type`
- `source_url`
- `format`
- `requester_ip`
- `session_id`
- `checkpoint_json`
- `stop_requested`
- `created_at`
- `started_at`
- `finished_at`
- `output_path`
- `error_code`

### Logs

Store:

- auth events
- admin actions
- job creation
- job pause/resume
- job completion/failure
- worker errors

## 7. API Outline

### Auth

- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/me`

### Jobs

- `POST /api/jobs`
- `GET /api/jobs/:id`
- `GET /api/jobs`
- `POST /api/jobs/:id/cancel`
- `POST /api/jobs/:id/pause`

### Admin

- `GET /api/admin/stats`
- `GET /api/admin/jobs`
- `GET /api/admin/logs`
- `POST /api/admin/jobs/:id/reprioritize`
- `POST /api/admin/jobs/:id/cancel`

### Worker/Internal

- internal dispatch endpoint
- internal heartbeat endpoint
- internal cleanup trigger

## 8. Build Phases

### Phase 1: Architecture Setup

- choose the exact stack for:
  - Vercel app
  - worker host
  - database
  - file storage
- create repo structure for frontend, backend/control plane, and worker
- define env var boundaries per service

### Phase 2: Identity and Access

- implement `/vip` and `/owner`
- add password-based sign-in
- add signed session cookies
- protect `/admin` for owner only

### Phase 3: Durable Job System

- create jobs schema
- build job submission flow
- build queue selection logic
- build checkpoint model

### Phase 4: Worker Implementation

- move download logic to worker
- run downloads in slices
- persist progress after each safe step
- upload final outputs
- update job status correctly

### Phase 5: Priority and Preemption

- add owner/VIP/public priority logic
- pause public jobs cooperatively
- resume paused public jobs automatically

### Phase 6: Limits and Safety

- public per-IP quotas
- queue caps
- playlist caps
- storage retention
- cleanup jobs
- worker retry rules

### Phase 7: Admin and Operations

- owner dashboard
- job inspection
- worker health
- privileged action logs
- cancellation controls

### Phase 8: Launch Hardening

- production config only
- secrets split by environment
- HTTPS-only deployment
- monitoring and error reporting
- retention rules

## 9. Acceptance Criteria

- public users can submit jobs without creating accounts
- VIP users use `/vip`
- owner users use `/owner`
- admin is owner-only
- queue state survives restarts
- public jobs no longer share in-memory state
- VIP and owner requests get predictable priority
- paused public jobs resume correctly
- outputs expire automatically
- logs exist for privileged actions and worker failures

## 10. Known Risks to Track During Rewrite

- trying to force the heavy download path into Vercel functions
- underestimating queue complexity
- letting the public tier exhaust free storage or bandwidth
- weak session or admin access design
- poor cleanup of temp outputs
- missing recovery after worker restarts

## 11. Suggested Deliverables

- architecture decision note
- schema and migrations
- auth implementation
- queue implementation
- worker implementation
- admin dashboard
- launch checklist completion
- deployment guide

## 12. Related Document

See also:

- `docs/LAUNCH_SECURITY_CHECKLIST.md`

