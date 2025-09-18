# Health & Task Reminder

A desktop application that helps you stay healthy and organized with customizable reminders for hydration, eye care, and task management.

## Features

### Hydration Reminder
- Customizable reminder intervals
- System notifications
- Status tracking
- Last reminder timestamp

### Eye Care Reminder
- Regular reminders to rest your eyes
- Customizable intervals
- Status tracking
- Last reminder timestamp

### Todo List
- Add tasks with due dates and times
- Mark tasks as complete
- Delete tasks
- Automatic notifications for due tasks
- Persistent storage (tasks are saved between sessions)

## Requirements

- Python 3.7 or higher
- Required packages (install using `pip install -r requirements.txt`):
  - customtkinter
  - pillow
  - plyer

## Installation

1. Clone or download this repository
2. Navigate to the project directory
3. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

## Usage

1. Run the application:
   ```
   python hydration_reminder.py
   ```

2. Use the tabs to switch between different features:
   - **Hydration**: Set your desired reminder interval and start/stop the reminder
   - **Eye Care**: Set your desired reminder interval and start/stop the reminder
   - **Todo List**: Add tasks with optional due dates and times

### Adding Tasks
- Enter the task description
- Optionally add a due date (YYYY-MM-DD format)
- Optionally add a due time (HH:MM format)
- Click "Add Task" to create the task

### Managing Tasks
- Click "Complete" to mark a task as done
- Click "Delete" to remove a task
- Tasks with due dates and times will trigger notifications when they're due

## Notes

- The application will show system notifications at your specified intervals
- Notifications will appear even when the application is minimized
- The last reminder time is displayed in each reminder tab
- Tasks are automatically saved to a `todos.json` file 