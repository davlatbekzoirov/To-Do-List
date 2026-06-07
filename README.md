# ⚡ TaskFlow

TaskFlow is a modern, responsive, and minimalist Django-based To-Do application. Built for individual productivity, it features user authentication, dynamic task filtering, urgency metrics dashboards, visual priority tracking, and automated background reminders.

---

## ✨ Features

* **🔒 Secure Authentication:** Built-in registration, login, and logout systems ensuring your tasks are completely private to your account.
* **📊 Dynamic Metrics Dashboard:** Real-time summary counters tracking your Total, Active, Completed, and Urgent tasks at a glance.
* **🔔 Time-Sensitive Notification Engine:** Proactive background worker scans your tasks and delivers in-app alert badges and emails 24 hours and 1 hour before deadlines.
* **🎨 Redesigned Visual Analytics:** Clean layout accented with intuitive color-coded borders and badges based on task priorities.
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

## 🛠️ Technology Stack

* **Backend Framework:** Django (Python)
* **Task Scheduler:** Celery (Asynchronous background worker)
* **Message Broker:** Redis
* **Database:** SQLite 3
* **Frontend UI:** Bootstrap 5 (with Glassmorphism accents)
* **Iconography:** FontAwesome 6

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

---

## 🚀 Quick Setup Guide

Get your local instance of TaskFlow up and running smoothly.

### 1. Environment Setup
Clone or download this repository, navigate to the project directory, and initialize a Python virtual environment:

```bash
# Create the virtual environment
python3 -m venv venv

# Activate the environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate