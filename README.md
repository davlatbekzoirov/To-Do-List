# ⚡ TaskFlow

TaskFlow is a modern, responsive, and minimalist Django-based To-Do application. Built for individual productivity, it features user authentication, dynamic task filtering, urgency metrics dashboards, visual priority tracking, automated background reminders, strict data security, and an integrated focus tracking engine.

---

## ✨ Features

* **🔒 Security, Governance & Compliance:** Built-in secure registration, login, and custom password complexity validators. Includes session inactivity timeout protection for shared devices and a tamper-proof internal AuditLog system to track high-level actions with hashed IP records.
* **🧠 Intelligent Focus & Pomodoro Engine:** A built-in 25-minute Pomodoro timer directly on individual task view pages that tracks focus sessions in real time and automatically records actual minutes spent to your account ledger.
* **📊 Dual Analytics Dashboard:** Visually displays task counts across categories alongside an advanced **Estimated Time vs. Actual Time Spent** comparison bar chart to measure personal efficiency.
* **🔔 Time-Sensitive Notification Engine:** Proactive background worker scans your tasks and delivers in-app alert badges and emails 24 hours and 1 hour before deadlines.
* **🔍 Power Filtering & Search:** Instantly narrow down workflows by status (Active/Completed), priority level, category, or text-based search queries.
* **⏰ Overdue Detection:** Automated checking mechanism that visually highlights tasks that have passed their target completion due date.

---

## 📸 Screenshots

### Main Dashboard & Analytics
<p align="center">
  <img src="dashboard.png" alt="TaskFlow Dashboard" width="100%">
</p>

<p align="center">
  <img src="analytics.png" alt="TaskFlow Analytics" width="100%">
</p>

### User Authentication & Organization
<p align="center">
  <img src="login.png" alt="Login Interface" width="32%">
  <img src="add_task.png" alt="Add Task Form" width="32%">
  <img src="categories.png" alt="Categories Management" width="32%">
</p>

---

## 🧠 How Celery is Used

TaskFlow relies on Celery and Redis to handle time-heavy calculations asynchronously in the background so the user interface never lags.

### 🕒 Scheduled Background Workflows
The automation logic is managed through specific background task routines defined in `todos/tasks.py`:

1. **`send_deadline_reminders` (Runs every 15 minutes):** Scans the active database to find tasks approaching their deadlines. It handles creating in-app alerts and processing reminder emails at exactly the **24-hour** and **1-hour** remaining milestones.
2. **`generate_daily_overdue_digests` (Runs every morning):** Pools overdue items for each user, updates the global overdue notification log, and dispatches a comprehensive diagnostic summary email directly to the user.

### ⚙️ Architecture Workflow
```text
[ Django Models ] ──> [ Celery Beat Clock ] ──> [ Redis Queue ] ──> [ Celery Worker ] ──> [ Live UI Notification ]