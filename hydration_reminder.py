import customtkinter as ctk
import tkinter as tk
from plyer import notification
import threading
import time
from PIL import Image, ImageTk
import os
from datetime import datetime, timedelta
import json
from tkcalendar import Calendar
from tkinter import ttk
import pystray
from PIL import Image, ImageDraw
import tkinter.messagebox as messagebox

class ReminderApp:
    def __init__(self):
        self.window = ctk.CTk()
        self.window.title("Health & Task Reminder")
        self.window.geometry("600x700")
        self.window.resizable(False, False)
        
        # Set theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Load saved settings
        self.load_settings()
        
        # Variables
        self.hydration_active = True  # Always active
        self.eye_active = True  # Always active
        self.hydration_thread = None
        self.eye_thread = None
        self.todos = []
        
        # Load todos from file if exists
        self.load_todos()
        
        self.setup_ui()
        self.setup_tray()
        
        # Start reminders automatically
        self.start_reminders()
        
        # Handle window close
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Countdown Timer Label
        self.countdown_seconds = 20 * 60  # 20 minutes in seconds
        self.timer_label = ctk.CTkLabel(
            self.window,
            text="Next reminder in: 20:00",
            font=("Helvetica", 18, "bold")
        )
        self.timer_label.pack(pady=10)
        self.update_countdown_timer()
    
    def setup_tray(self):
        # Create a simple icon
        icon_image = Image.new('RGB', (64, 64), color='blue')
        dc = ImageDraw.Draw(icon_image)
        dc.rectangle([16, 16, 48, 48], fill='white')
        
        # Create menu items
        menu = (
            pystray.MenuItem('Show', self.show_window),
            pystray.MenuItem('Exit', self.quit_app)
        )
        
        # Create the system tray icon
        self.icon = pystray.Icon("reminder", icon_image, "Health & Task Reminder", menu)
        
        # Start the icon in a separate thread
        threading.Thread(target=self.icon.run, daemon=True).start()
    
    def show_window(self):
        self.window.deiconify()
        self.window.lift()
    
    def quit_app(self):
        # Stop all reminders
        self.hydration_active = False
        self.eye_active = False
        self.save_settings()
        
        # Stop the icon
        self.icon.stop()
        
        # Destroy the window
        self.window.destroy()
    
    def on_closing(self):
        # Hide the window instead of closing
        self.window.withdraw()
        notification.notify(
            title="Health & Task Reminder",
            message="App is running in the background. Right-click the tray icon to show or exit.",
            timeout=5
        )
    
    def load_settings(self):
        try:
            with open("settings.json", "r") as f:
                self.settings = json.load(f)
        except FileNotFoundError:
            self.settings = {
                'hydration_active': True,
                'eye_active': True
            }
    
    def save_settings(self):
        with open("settings.json", "w") as f:
            json.dump(self.settings, f)
    
    def setup_ui(self):
        # Title
        title_label = ctk.CTkLabel(
            self.window,
            text="Todo List with Health Reminders",
            font=("Helvetica", 24, "bold")
        )
        title_label.pack(pady=20)
        
        # Status Label
        self.status_label = ctk.CTkLabel(
            self.window,
            text="Health Reminders: Active (20 min intervals)",
            font=("Helvetica", 14)
        )
        self.status_label.pack(pady=10)
        
        # Add Todo Frame
        add_frame = ctk.CTkFrame(self.window)
        add_frame.pack(pady=10, padx=20, fill="x")
        
        # Task Entry
        self.task_entry = ctk.CTkEntry(
            add_frame,
            placeholder_text="Enter task",
            width=200
        )
        self.task_entry.pack(side="left", padx=5, pady=10)
        
        # Date Button
        self.date_button = ctk.CTkButton(
            add_frame,
            text="Select Date",
            command=self.show_date_picker,
            width=100
        )
        self.date_button.pack(side="left", padx=5, pady=10)
        
        # Time Button
        self.time_button = ctk.CTkButton(
            add_frame,
            text="Select Time",
            command=self.show_time_picker,
            width=100
        )
        self.time_button.pack(side="left", padx=5, pady=10)
        
        # Add Button
        add_button = ctk.CTkButton(
            add_frame,
            text="Add Task",
            command=self.add_todo,
            width=100
        )
        add_button.pack(side="left", padx=5, pady=10)
        
        # Selected date/time labels in a new row
        label_frame = ctk.CTkFrame(self.window)
        label_frame.pack(pady=0, padx=20, fill="x")
        self.selected_date = None
        self.selected_time = None
        self.date_label = ctk.CTkLabel(
            label_frame,
            text="",
            font=("Helvetica", 12)
        )
        self.date_label.pack(side="left", padx=5, pady=5)
        self.time_label = ctk.CTkLabel(
            label_frame,
            text="",
            font=("Helvetica", 12)
        )
        self.time_label.pack(side="left", padx=5, pady=5)
        
        # Todo List Frame
        self.todo_frame = ctk.CTkScrollableFrame(self.window)
        self.todo_frame.pack(pady=10, padx=20, fill="both", expand=True)
        
        # Refresh todo list
        self.refresh_todo_list()
        
        self.date_picker_open = False
        self.time_picker_open = False
    
    def start_reminders(self):
        # Start hydration reminder
        self.hydration_thread = threading.Thread(
            target=self.reminder_loop,
            args=(20, "hydration", "Time to Hydrate! 💧", None)
        )
        self.hydration_thread.daemon = True
        self.hydration_thread.start()
        
        # Start eye care reminder
        self.eye_thread = threading.Thread(
            target=self.reminder_loop,
            args=(20, "eye", "Time to rest your eyes! 👀", None)
        )
        self.eye_thread.daemon = True
        self.eye_thread.start()
    
    def show_date_picker(self):
        if self.date_picker_open:
            return
        self.date_picker_open = True
        # Create a new top-level window
        date_window = tk.Toplevel(self.window)
        date_window.title("Select Date")
        date_window.geometry("300x300")
        date_window.protocol("WM_DELETE_WINDOW", lambda: self._on_close_date_picker(date_window))
        # Create calendar widget
        cal = Calendar(date_window, selectmode='day', date_pattern='yyyy-mm-dd')
        cal.pack(pady=20, padx=20)
        # Add select button
        def select_date():
            self.selected_date = cal.get_date()
            self.date_label.configure(text=f"Date: {self.selected_date}")
            self.date_picker_open = False
            date_window.destroy()
        select_button = ctk.CTkButton(
            date_window,
            text="Select",
            command=select_date
        )
        select_button.pack(pady=10)
    def _on_close_date_picker(self, window):
        self.date_picker_open = False
        window.destroy()
    
    def show_time_picker(self):
        if self.time_picker_open:
            return
        self.time_picker_open = True
        # Create a new top-level window
        time_window = tk.Toplevel(self.window)
        time_window.title("Select Time")
        time_window.geometry("400x250")  # Increased width and height
        time_window.protocol("WM_DELETE_WINDOW", lambda: self._on_close_time_picker(time_window))
        # Create time selection widgets
        hour_var = tk.StringVar(value="12")
        minute_var = tk.StringVar(value="00")
        ampm_var = tk.StringVar(value="AM")
        time_frame = ctk.CTkFrame(time_window)
        time_frame.pack(pady=20, padx=20)
        # Hour selection
        hour_label = ctk.CTkLabel(time_frame, text="Hour:")
        hour_label.pack(side="left", padx=5)
        hour_spinbox = ttk.Spinbox(
            time_frame,
            from_=1,
            to=12,
            width=5,
            textvariable=hour_var,
            format="%02.0f"
        )
        hour_spinbox.pack(side="left", padx=5)
        # Minute selection
        minute_label = ctk.CTkLabel(time_frame, text="Minute:")
        minute_label.pack(side="left", padx=5)
        minute_spinbox = ttk.Spinbox(
            time_frame,
            from_=0,
            to=59,
            width=5,
            textvariable=minute_var,
            format="%02.0f"
        )
        minute_spinbox.pack(side="left", padx=5)
        # AM/PM selection
        ampm_label = ctk.CTkLabel(time_frame, text="AM/PM:")
        ampm_label.pack(side="left", padx=5)
        ampm_combobox = ttk.Combobox(
            time_frame,
            textvariable=ampm_var,
            values=["AM", "PM"],
            width=5,
            state="readonly"
        )
        ampm_combobox.pack(side="left", padx=5)
        # Add select button
        def select_time():
            hour = int(hour_var.get())
            if ampm_var.get() == "PM" and hour != 12:
                hour += 12
            elif ampm_var.get() == "AM" and hour == 12:
                hour = 0
            self.selected_time = f"{hour:02d}:{minute_var.get()}"
            display_time = f"{hour_var.get()}:{minute_var.get()} {ampm_var.get()}"
            self.time_label.configure(text=f"Time: {display_time}")
            self.time_picker_open = False
            time_window.destroy()
        select_button = ctk.CTkButton(
            time_window,
            text="Select",
            command=select_time
        )
        select_button.pack(pady=10)
    def _on_close_time_picker(self, window):
        self.time_picker_open = False
        window.destroy()
    
    def add_todo(self):
        task = self.task_entry.get()
        
        # Require both date and time
        if not task:
            return
        if not self.selected_date or not self.selected_time:
            messagebox.showwarning("Missing Date/Time", "Please select both date and time before adding the task.")
            return
        
        todo = {
            "task": task,
            "date": self.selected_date,
            "time": self.selected_time,
            "completed": False
        }
        
        self.todos.append(todo)
        self.save_todos()
        self.refresh_todo_list()
        
        # Clear entries
        self.task_entry.delete(0, tk.END)
        self.selected_date = None
        self.selected_time = None
        self.date_label.configure(text="")
        self.time_label.configure(text="")
        
        # Schedule notification if date and time are set
        if todo["date"] and todo["time"]:
            self.schedule_todo_notification(todo)
    
    def refresh_todo_list(self):
        # Clear existing todos
        for widget in self.todo_frame.winfo_children():
            widget.destroy()
            
        # Add todos to frame
        for i, todo in enumerate(self.todos):
            todo_frame = ctk.CTkFrame(self.todo_frame)
            todo_frame.pack(fill="x", pady=5, padx=5)
            
            # Task label
            task_text = todo["task"]
            if todo["date"]:
                task_text += f" (Due: {todo['date']}"
                if todo["time"]:
                    task_text += f" at {todo['time']}"
                task_text += ")"
                
            task_label = ctk.CTkLabel(
                todo_frame,
                text=task_text,
                font=("Helvetica", 12)
            )
            task_label.pack(side="left", padx=5, pady=5)
            
            # Complete button
            if not todo["completed"]:
                complete_button = ctk.CTkButton(
                    todo_frame,
                    text="Complete",
                    command=lambda idx=i: self.complete_todo(idx),
                    width=80
                )
                complete_button.pack(side="right", padx=5, pady=5)
            
            # Delete button
            delete_button = ctk.CTkButton(
                todo_frame,
                text="Delete",
                command=lambda idx=i: self.delete_todo(idx),
                width=80,
                fg_color="red"
            )
            delete_button.pack(side="right", padx=5, pady=5)
    
    def complete_todo(self, index):
        self.todos[index]["completed"] = True
        self.save_todos()
        self.refresh_todo_list()
    
    def delete_todo(self, index):
        del self.todos[index]
        self.save_todos()
        self.refresh_todo_list()
    
    def save_todos(self):
        with open("todos.json", "w") as f:
            json.dump(self.todos, f)
    
    def load_todos(self):
        try:
            with open("todos.json", "r") as f:
                self.todos = json.load(f)
        except FileNotFoundError:
            self.todos = []
    
    def schedule_todo_notification(self, todo):
        if todo["date"] and todo["time"]:
            try:
                reminder_time = datetime.strptime(f"{todo['date']} {todo['time']}", "%Y-%m-%d %H:%M")
                now = datetime.now()
                
                if reminder_time > now:
                    delay = (reminder_time - now).total_seconds()
                    threading.Timer(delay, self.show_todo_notification, args=[todo]).start()
            except ValueError:
                pass
    
    def show_todo_notification(self, todo):
        notification.notify(
            title="Todo Reminder",
            message=f"Task due: {todo['task']}",
            timeout=10
        )
    
    def reminder_loop(self, interval, reminder_type, message, last_label):
        while getattr(self, f"{reminder_type}_active"):
            # Calculate the next reminder time
            next_reminder = time.time() + (interval * 60)
            
            # Sleep in smaller chunks to allow for quicker response to changes
            while time.time() < next_reminder and getattr(self, f"{reminder_type}_active"):
                time.sleep(1)  # Sleep for 1 second at a time
                
            if getattr(self, f"{reminder_type}_active"):  # Check if still active after sleep
                notification.notify(
                    title=message,
                    message="Take a break and stay healthy!",
                    timeout=10
                )
    
    def update_countdown_timer(self):
        mins, secs = divmod(self.countdown_seconds, 60)
        self.timer_label.configure(text=f"Next reminder in: {mins:02d}:{secs:02d}")
        if self.countdown_seconds > 0:
            self.countdown_seconds -= 1
            self.window.after(1000, self.update_countdown_timer)
        else:
            # Trigger both reminders
            self.show_reminder_popup("Time to Hydrate! 💧\nTime to rest your eyes! 👀")
            try:
                notification.notify(
                    title="Health Reminder",
                    message="Time to Hydrate! 💧\nTime to rest your eyes! 👀",
                    timeout=10
                )
            except Exception:
                pass
            self.countdown_seconds = 20 * 60
            self.window.after(1000, self.update_countdown_timer)

    def show_reminder_popup(self, message):
        try:
            messagebox.showinfo("Health Reminder", message)
        except Exception:
            pass
    
    def run(self):
        self.window.mainloop()

if __name__ == "__main__":
    app = ReminderApp()
    app.run() 