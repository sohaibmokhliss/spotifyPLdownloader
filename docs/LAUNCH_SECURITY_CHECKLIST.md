# Launch Security Checklist and Rewrite Plan

This file is a planning note for later work. It does not describe functionality that is already implemented.

## Goal

Rewrite the current Flask downloader into a Vercel-friendly product with:

- a public interface for strangers
- a `/vip` login for the shared friends-and-family VIP account
- an `/owner` login for the owner account
- owner and VIP priority over public jobs
- a real launch checklist for the security and hosting work that needs to happen before release

## Product Direction

### Roles

- `public`
  - anonymous users
  - can use the public downloader
  - lowest queue priority
- `vip`
  - one shared account for family and close friends
  - route: `/vip`
  - higher priority than public
- `owner`
  - one shared owner account
  - route: `/owner`
  - highest priority
  - can access admin and operational controls

### Hosting Direction

Do not try to run the real downloader entirely on Vercel.

Use this split instead:

- Vercel
  - frontend
  - auth/session handling
  - job submission
  - job status pages
- separate worker service
  - runs `yt-dlp`
  - runs FFmpeg
  - handles long-running download jobs
  - processes queue slices and checkpoints
- database/storage
  - stores jobs, roles, logs, checkpoints, and temporary outputs

### Route Plan

- `/`
  - public landing page and anonymous downloader
- `/vip`
  - VIP login page
- `/owner`
  - owner login page
- `/admin`
  - owner-only admin and operations page

### Queue and Priority Rules

- Start with one active worker slot to stay conservative on free-tier hosting.
- Priority order:
  - `owner`
  - `vip`
  - `public`
- Public jobs are allowed, but they are preemptible.
- If a VIP or owner job arrives while a public job is running:
  - the public job is paused at the next safe checkpoint
  - the higher-priority job runs next
- Preemption should be cooperative, not a hard kill in the middle of a file.
- Paused public jobs should resume automatically when no owner or VIP job is waiting.

### Public Limits

Keep public access open, but impose hard limits so strangers cannot exhaust free resources.

- max 1 queued or running job per IP
- max 5 jobs per day per IP
- max 20 items per playlist for public jobs
- short output retention window

### VIP and Owner Limits

- VIP
  - max 2 queued or running jobs
  - larger playlist cap than public
- Owner
  - max 3 queued or running jobs
  - highest priority
  - can cancel or reprioritize jobs from admin

## Suggested Data Model

Create a durable `jobs` table with enough information to pause and resume work safely.

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

Use role values:

- `public`
- `vip`
- `owner`

Use status values:

- `queued`
- `running`
- `paused`
- `completed`
- `failed`
- `expired`
- `canceled`

## Launch Checklist

### Blockers

- Risk: shared global download state
  - Why it matters: one user can affect another user's jobs and progress
  - Recommended fix: replace in-memory progress with durable per-job state in the database
  - Launch blocker: yes

- Risk: long-running synchronous download requests
  - Why it matters: requests can hang, fail, or exceed serverless/runtime limits
  - Recommended fix: move downloads into a worker queue with resumable slices
  - Launch blocker: yes

- Risk: Vercel-incompatible runtime assumptions
  - Why it matters: `yt-dlp`, FFmpeg, temp files, and long jobs are a bad fit for Vercel-only hosting
  - Recommended fix: keep Vercel for the UI and control plane only; run downloads in a separate worker service
  - Launch blocker: yes

- Risk: no durable queue
  - Why it matters: jobs are lost on restart and priority cannot be enforced safely
  - Recommended fix: add a persistent jobs table and scheduler logic
  - Launch blocker: yes

- Risk: no role-based auth model for public, VIP, and owner
  - Why it matters: the new split cannot be enforced safely without real roles and protected routes
  - Recommended fix: implement separate session-based auth for `/vip`, `/owner`, and `/admin`
  - Launch blocker: yes

- Risk: admin still depends on Basic Auth
  - Why it matters: Basic Auth is weak operationally and should not be the final owner access model
  - Recommended fix: replace it with real owner sessions
  - Launch blocker: yes

- Risk: no abuse controls for the public interface
  - Why it matters: strangers can flood the downloader and exhaust CPU, bandwidth, and storage
  - Recommended fix: add per-IP quotas, queue caps, and playlist caps
  - Launch blocker: yes

- Risk: no VIP priority enforcement
  - Why it matters: the product promise for VIP and owner users cannot be honored
  - Recommended fix: implement queue priority and cooperative preemption
  - Launch blocker: yes

- Risk: debug mode enabled in the current app
  - Why it matters: debug mode is not acceptable for production exposure
  - Recommended fix: disable debug mode and move to production runtime settings
  - Launch blocker: yes

- Risk: IP logging without retention rules
  - Why it matters: logs can accumulate indefinitely and create privacy and operations problems
  - Recommended fix: set retention period, cleanup job, and minimum log fields
  - Launch blocker: yes

- Risk: weak temp-file and output cleanup
  - Why it matters: failed jobs and abandoned downloads can leak storage
  - Recommended fix: add TTL cleanup for temp files and finished outputs
  - Launch blocker: yes

- Risk: no storage budget controls
  - Why it matters: free-tier storage can be exhausted quickly by public use
  - Recommended fix: impose file-size caps, retention windows, and automatic deletion
  - Launch blocker: yes

- Risk: no worker restart recovery
  - Why it matters: crashes and redeploys can strand jobs forever
  - Recommended fix: save checkpoints and add retry and recovery behavior
  - Launch blocker: yes

- Risk: secrets are not cleanly separated by service
  - Why it matters: frontend, worker, and admin secrets should not all live in one security boundary
  - Recommended fix: separate secrets by service and environment
  - Launch blocker: yes

### Important but Not Immediate Blockers

- Risk: no audit trail for privileged actions
  - Why it matters: owner and VIP actions cannot be reviewed later
  - Recommended fix: log sign-ins, cancellations, priority changes, and admin actions
  - Launch blocker: no

- Risk: no clear operational dashboard for queue health
  - Why it matters: it will be hard to debug worker failures or stuck jobs
  - Recommended fix: add owner-only queue, worker, and storage visibility in admin
  - Launch blocker: no

## Acceptance Criteria for the Rewrite

- Public users can use `/` without logging in.
- VIP users log in at `/vip`.
- Owner users log in at `/owner`.
- `/admin` is owner-only and is not advertised in the public UI.
- Public jobs are isolated per session and per IP.
- VIP and owner jobs reliably outrank public jobs.
- Public jobs pause safely when a VIP or owner job needs the worker.
- Jobs survive worker restart and can resume from checkpoints.
- Output cleanup is automatic.
- Public abuse limits are enforced.
- Debug mode is off in production.

## Recommended Work Order

1. Design the new architecture and pick the worker plus database stack.
2. Build roles, session auth, and the `/vip` and `/owner` flows.
3. Add the durable jobs table and queue scheduler.
4. Move download execution into the worker with checkpoints.
5. Add VIP and owner priority plus public preemption.
6. Add public abuse controls and storage retention.
7. Replace current admin auth with owner-only session access.
8. Finish admin visibility and audit logs.

