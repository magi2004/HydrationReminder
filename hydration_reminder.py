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
import sys
import ctypes
try:
    import winreg as _winreg
except Exception:
    _winreg = None

def get_resource_path(relative_path: str) -> str:
    try:
        base_path = sys._MEIPASS  # type: ignore[attr-defined]
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def set_app_user_model_id(app_id: str) -> None:
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)  # type: ignore[attr-defined]
    except Exception:
        pass

def get_app_data_dir() -> str:
    appdata = os.getenv("APPDATA")
    if not appdata:
        appdata = os.path.expanduser("~")
    target = os.path.join(appdata, "HydrationReminder")
    try:
        os.makedirs(target, exist_ok=True)
    except Exception:
        pass
    return target

class ReminderApp:
    def __init__(self):
        # Ensure Windows toast notifications are associated with our app
        set_app_user_model_id("HydrationReminder.HealthTaskReminder")

        self.window = ctk.CTk()
        self.window.title("Health & Task Reminder")
        self.window.geometry("600x700")
        self.window.resizable(False, False)
        try:
            icon_path = get_resource_path("icon.ico")
            if os.path.exists(icon_path):
                try:
                    self.window.iconbitmap(icon_path)
                except Exception:
                    pass
        except Exception:
            pass
        
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
        self.register_startup(enable=True)
        
        # Start reminders automatically (only via unified countdown popup)
        # Disable background threads to avoid duplicate notifications
        # self.start_reminders()
        
        # Handle window close
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.countdown_seconds = 20 * 60  # 20 minutes in seconds
        self.update_countdown_timer()
    
    def setup_tray(self):
        # Load icon from file or fallback
        try:
            icon_path = get_resource_path("icon.ico")
            if os.path.exists(icon_path):
                icon_image = Image.open(icon_path)
            else:
                raise FileNotFoundError
        except Exception:
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
        self.window.after(0, self._show_window_safe)
        
    def _show_window_safe(self):
        self.window.deiconify()
        self.window.lift()
    
    def quit_app(self):
        # Stop all reminders
        self.hydration_active = False
        self.eye_active = False
        self.save_settings()
        
        # Stop the icon
        self.icon.stop()
        
        # Destroy the window safely on main thread
        self.window.after(0, self.window.destroy)
    
    def on_closing(self):
        # Hide the window instead of closing
        self.window.withdraw()
        self.safe_notify(
            title="Health & Task Reminder",
            message="App is running in the background. Right-click the tray icon to show or exit.",
            timeout=5
        )
    
    def load_settings(self):
        try:
            settings_path = os.path.join(get_app_data_dir(), "settings.json")
            with open(settings_path, "r") as f:
                self.settings = json.load(f)
        except FileNotFoundError:
            self.settings = {
                'hydration_active': True,
                'eye_active': True
            }
    
    def save_settings(self):
        try:
            settings_path = os.path.join(get_app_data_dir(), "settings.json")
            with open(settings_path, "w") as f:
                json.dump(self.settings, f)
        except Exception:
            pass
    
    def setup_ui(self):
        # Configure grid layout for the main window
        self.window.grid_columnconfigure(0, weight=1)
        self.window.grid_rowconfigure(2, weight=1)  # Todo list expands

        # --- Hero Section (Header & Timer) ---
        self.hero_frame = ctk.CTkFrame(self.window, fg_color="transparent")
        self.hero_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        
        # Title
        title_label = ctk.CTkLabel(
            self.hero_frame,
            text="Hydration & Focus",
            font=("Roboto Medium", 24),
            text_color=("gray40", "gray80")
        )
        title_label.pack(anchor="center")
        
        # Big Countdown Timer (Hero Element)
        self.timer_label = ctk.CTkLabel(
            self.hero_frame,
            text="20:00",
            font=("Roboto", 64, "bold"),
            text_color=("#3B8ED0", "#1F6AA5")  # CustomTKinter blue accent
        )
        self.timer_label.pack(anchor="center", pady=(5, 10))

        self.status_label = ctk.CTkLabel(
            self.hero_frame,
            text="Next wellness check",
            font=("Roboto", 12),
            text_color=("gray50", "gray70")
        )
        self.status_label.pack(anchor="center")

        # --- Add Task Section ---
        self.add_frame = ctk.CTkFrame(self.window, corner_radius=10)
        self.add_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=10)
        self.add_frame.grid_columnconfigure(0, weight=1) # Entry expands

        # Row 1: Entry
        self.task_entry = ctk.CTkEntry(
            self.add_frame,
            placeholder_text="What do you need to get done?",
            height=40,
            font=("Roboto", 14),
            border_width=0,
            fg_color=("gray90", "gray20")
        )
        self.task_entry.grid(row=0, column=0, columnspan=3, sticky="ew", padx=10, pady=(10, 5))

        # Row 2: Controls & Actions
        self.controls_frame = ctk.CTkFrame(self.add_frame, fg_color="transparent")
        self.controls_frame.grid(row=1, column=0, columnspan=3, sticky="ew", padx=10, pady=(0, 10))
        
        # Date & Time Pickers
        self.date_button = ctk.CTkButton(
            self.controls_frame,
            text="📅 Date",
            command=self.show_date_picker,
            width=80,
            height=32,
            fg_color="transparent",
            border_width=1,
            text_color=("gray40", "gray80")
        )
        self.date_button.pack(side="left", padx=(0, 5))

        self.time_button = ctk.CTkButton(
            self.controls_frame,
            text="⏰ Time",
            command=self.show_time_picker,
            width=80,
            height=32,
            fg_color="transparent",
            border_width=1,
            text_color=("gray40", "gray80")
        )
        self.time_button.pack(side="left", padx=5)

        # Selected Info Display (Small text)
        self.selection_info_label = ctk.CTkLabel(
            self.controls_frame,
            text="",
            font=("Roboto", 11),
            text_color="gray60"
        )
        self.selection_info_label.pack(side="left", padx=10)
        
        # Add Button (Primary Action)
        add_button = ctk.CTkButton(
            self.controls_frame,
            text="Add Task",
            command=self.add_todo,
            width=100,
            height=32,
            font=("Roboto", 13, "bold")
        )
        add_button.pack(side="right")
        
        # Keep references for logic to use (adapting old variables to new UI)
        self.date_label = self.selection_info_label # Mapping old prop to new label for compat
        self.time_label = self.selection_info_label # Reuse same label for simplicity or update method

        # --- Todo List Section ---
        self.todo_frame = ctk.CTkScrollableFrame(
            self.window,
            label_text="Your Tasks",
            label_font=("Roboto Medium", 14),
            corner_radius=10
        )
        self.todo_frame.grid(row=2, column=0, sticky="nsew", padx=20, pady=(10, 20))
        
        # Initialize helper parsing variables
        self.selected_date = None
        self.selected_time = None
        
        # Refresh todo list
        self.refresh_todo_list()
        
        self.date_picker_open = False
        self.time_picker_open = False
    
    def start_reminders(self):
        # Deprecated: unified reminders handled by countdown timer
        return
    
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
            self.selected_date = cal.get_date()
            self.selection_info_label.configure(text=f"📅 {self.selected_date}")
            self.date_picker_open = False
            date_window.destroy()
            # Open time picker immediately after selecting date
            self.show_time_picker()
        select_button = ctk.CTkButton(
            date_window,
            text="Next ➔",
            command=select_date,
            font=("Roboto", 13, "bold")
        )
        select_button.pack(pady=10)
    def _on_close_date_picker(self, window):
        self.date_picker_open = False
        window.destroy()
    
    def show_time_picker(self):
        if self.time_picker_open:
            return
        self.time_picker_open = True
        # Require a selected date to validate against current time
        if not self.selected_date:
            try:
                messagebox.showwarning("Missing Date", "Please select a date first.")
            except Exception:
                pass
            self.time_picker_open = False
            return
        # Create a new top-level window
        time_window = tk.Toplevel(self.window)
        time_window.title("Select Time")
        time_window.geometry("400x250")  # Increased width and height
        time_window.protocol("WM_DELETE_WINDOW", lambda: self._on_close_time_picker(time_window))
        # Create time selection widgets
        now = datetime.now()
        hour_12 = now.hour % 12 or 12
        ampm_default = "AM" if now.hour < 12 else "PM"
        hour_var = tk.StringVar(value=f"{hour_12:02d}")
        minute_var = tk.StringVar(value=f"{now.minute:02d}")
        ampm_var = tk.StringVar(value=ampm_default)
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
            display_time = f"{hour:02d}:{minute_var.get()} {ampm_var.get()}"
            # Validate not in the past
            try:
                selected_dt = datetime.strptime(f"{self.selected_date} {self.selected_time}", "%Y-%m-%d %H:%M")
                if selected_dt <= datetime.now():
                    try:
                        messagebox.showwarning("Invalid Time", "Please select a future time.")
                    except Exception:
                        pass
                    return
            except Exception:
                pass
            
            # Update the unified info label
            current_text = f"📅 {self.selected_date}"
            self.selection_info_label.configure(text=f"{current_text}  •  ⏰ {self.selected_time}")
            
            self.time_picker_open = False
            time_window.destroy()
        select_button = ctk.CTkButton(
            time_window,
            text="Confirm Time",
            command=select_time,
             font=("Roboto", 13, "bold")
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
            "completed": False,
            "daily": False
        }
        
        self.todos.append(todo)
        self.save_todos()
        self.refresh_todo_list()
        
        # Clear entries
        self.task_entry.delete(0, tk.END)
        self.selected_date = None
        self.selected_time = None
        # Reset specific label
        self.selection_info_label.configure(text="")
        
        # Schedule notification if date and time are set
        if todo["date"] and todo["time"]:
            self.schedule_todo_notification(todo)
    
    def refresh_todo_list(self):
        # Clear existing todos
        for widget in self.todo_frame.winfo_children():
            widget.destroy()
            
        # Add todos to frame
        for i, todo in enumerate(self.todos):
            # Card Frame
            todo_card = ctk.CTkFrame(
                self.todo_frame,
                fg_color=("gray95", "gray17"), # Slightly lighter/different than background
                corner_radius=8
            )
            todo_card.pack(fill="x", pady=4, padx=5)
            
            # --- Left side: Task Info ---
            info_frame = ctk.CTkFrame(todo_card, fg_color="transparent")
            info_frame.pack(side="left", fill="both", expand=True, padx=10, pady=5)
            
            # Strikethrough effect logic could go here, but for now just dim color if completed
            text_color = "gray50" if todo["completed"] else ("gray10", "gray90")
            font_style = ("Roboto", 14)
            
            task_label = ctk.CTkLabel(
                info_frame,
                text=todo["task"],
                font=font_style,
                text_color=text_color,
                anchor="w"
            )
            task_label.pack(fill="x")
            
            # Date/Time subtext
            if todo["date"] or todo["time"]:
                due_text = f"📅 {todo['date']}" if todo['date'] else ""
                if todo['time']:
                    due_text += f" • ⏰ {todo['time']}"
                if todo.get("daily"):
                    due_text += " • 🔄 Daily"
                    
                sub_label = ctk.CTkLabel(
                    info_frame,
                    text=due_text,
                    font=("Roboto", 11),
                    text_color="gray60",
                    anchor="w"
                )
                sub_label.pack(fill="x")

            # --- Right side: Actions ---
            actions_frame = ctk.CTkFrame(todo_card, fg_color="transparent")
            actions_frame.pack(side="right", padx=10)

            # Daily toggle (Simplified to just an Icon/Checkbox or keep switch if preferred, sticking to switch for functionality)
            # Using a smaller switch
            daily_var = tk.BooleanVar(value=todo.get("daily", False))
            def make_toggle_handler(index, var):
                return lambda: self.toggle_daily(index, var.get())
            
            # Tooltip-ish text or just icon could be better, but switch is clear
            daily_switch = ctk.CTkSwitch(
                actions_frame,
                text="Daily",
                font=("Roboto", 11),
                command=make_toggle_handler(i, daily_var),
                variable=daily_var,
                width=60,
                height=20,
                switch_width=30,
                switch_height=16
            )
            daily_switch.pack(side="left", padx=5)

            # Complete Action
            if not todo["completed"]:
                complete_btn = ctk.CTkButton(
                    actions_frame,
                    text="✔",
                    width=30,
                    height=30,
                    corner_radius=15, # Circular
                    fg_color="#2CC985",
                    hover_color="#229C68",
                    command=lambda idx=i: self.complete_todo(idx)
                )
                complete_btn.pack(side="left", padx=5)
            
            # Delete Action
            delete_btn = ctk.CTkButton(
                actions_frame,
                text="✕",
                width=30,
                height=30,
                corner_radius=15, # Circular
                fg_color="transparent",
                text_color="gray50",
                hover_color=("gray80", "gray30"),
                border_width=1,
                border_color=("gray70", "gray40"),
                command=lambda idx=i: self.delete_todo(idx)
            )
            delete_btn.pack(side="right", padx=5)
    
    def complete_todo(self, index):
        self.todos[index]["completed"] = True
        self.save_todos()
        self.refresh_todo_list()

    def toggle_daily(self, index, value):
        self.todos[index]["daily"] = bool(value)
        self.save_todos()
        # Reschedule if necessary
        try:
            self.schedule_todo_notification(self.todos[index])
        except Exception:
            pass
    
    def delete_todo(self, index):
        del self.todos[index]
        self.save_todos()
        self.refresh_todo_list()
    
    def save_todos(self):
        try:
            todos_path = os.path.join(get_app_data_dir(), "todos.json")
            with open(todos_path, "w") as f:
                json.dump(self.todos, f)
        except Exception:
            pass
    
    def load_todos(self):
        try:
            todos_path = os.path.join(get_app_data_dir(), "todos.json")
            with open(todos_path, "r") as f:
                self.todos = json.load(f)
        except FileNotFoundError:
            self.todos = []
    
    def schedule_todo_notification(self, todo):
        if todo["date"] and todo["time"]:
            try:
                reminder_time = datetime.strptime(f"{todo['date']} {todo['time']}", "%Y-%m-%d %H:%M")
                now = datetime.now()
                
                if reminder_time <= now:
                    # If daily is enabled, schedule for next day at the same time
                    if todo.get("daily"):
                        reminder_time = reminder_time + timedelta(days=1)
                    else:
                        return

                delay = (reminder_time - now).total_seconds()
                def notify_and_reschedule():
                    self.show_todo_notification(todo)
                    if todo.get("daily"):
                        # reschedule for next day
                        try:
                            todo_date = datetime.strptime(todo['date'], "%Y-%m-%d").date()
                            next_day = (datetime.combine(todo_date, datetime.min.time()) + timedelta(days=1)).date()
                            todo['date'] = next_day.strftime("%Y-%m-%d")
                            self.save_todos()
                        except Exception:
                            pass
                        self.schedule_todo_notification(todo)
                threading.Timer(delay, notify_and_reschedule).start()
            except ValueError:
                pass
    
    def show_todo_notification(self, todo):
        # Use unified, top-most popup similar to health reminder
        self.show_unified_todo_popup(todo)

    def show_unified_todo_popup(self, todo):
        try:
            popup = tk.Toplevel(self.window)
            popup.title("Todo Reminder")
            popup.attributes("-topmost", True)
            popup.geometry("460x240")
            try:
                popup.iconbitmap(get_resource_path("icon.ico"))
            except Exception:
                pass
            popup.grab_set()
            popup.protocol("WM_DELETE_WINDOW", lambda: None)
            frame = ctk.CTkFrame(popup)
            frame.pack(fill="both", expand=True, padx=15, pady=15)
            due_str = ""
            try:
                if todo.get("date") and todo.get("time"):
                    due_str = f"\nDue: {todo['date']} {todo['time']}"
            except Exception:
                pass
            label = ctk.CTkLabel(
                frame,
                text=f"Task due: {todo['task']}" + due_str,
                font=("Helvetica", 18, "bold"),
                justify="center"
            )
            label.pack(pady=20)
            btn = ctk.CTkButton(frame, text="OK", command=lambda: self._close_unified_popup(popup), width=120)
            btn.pack(pady=10)
            popup.after(60_000, lambda: self._close_unified_popup(popup))
            popup.after(200, lambda: popup.attributes("-topmost", True))
        except Exception:
            pass
    
    def reminder_loop(self, interval, reminder_type, message, last_label):
        # Deprecated: unified reminders handled by countdown timer
        return
    
    def update_countdown_timer(self):
        if self.countdown_seconds > 0:
            self.countdown_seconds -= 1
        else:
            # Trigger reminders
            self.show_unified_reminder_popup()
            self.countdown_seconds = 20 * 60

        # Only update GUI if window is visible (normal state) to save CPU
        try:
            if self.window.state() == "normal":
                mins, secs = divmod(self.countdown_seconds, 60)
                self.timer_label.configure(text=f"{mins:02d}:{secs:02d}")
        except Exception:
            pass
            
        self.window.after(1000, self.update_countdown_timer)

    def show_reminder_popup(self, message):
        # Deprecated in favor of show_unified_reminder_popup
        self.show_unified_reminder_popup()

    def show_unified_reminder_popup(self):
        try:
            popup = tk.Toplevel(self.window)
            popup.title("Health Reminder")
            popup.attributes("-topmost", True)
            popup.geometry("420x220")
            try:
                popup.iconbitmap(get_resource_path("icon.ico"))
            except Exception:
                pass
            popup.grab_set()
            # Prevent closing to ensure attention until timeout or OK
            popup.protocol("WM_DELETE_WINDOW", lambda: None)
            frame = ctk.CTkFrame(popup)
            frame.pack(fill="both", expand=True, padx=15, pady=15)
            label = ctk.CTkLabel(
                frame,
                text="Time to Hydrate! 💧\nTime to rest your eyes! 👀",
                font=("Helvetica", 18, "bold"),
                justify="center"
            )
            label.pack(pady=20)
            btn = ctk.CTkButton(frame, text="OK", command=lambda: self._close_unified_popup(popup), width=120)
            btn.pack(pady=10)
            # Auto-close after 60 seconds if not acknowledged
            popup.after(60_000, lambda: self._close_unified_popup(popup))
            # Force on top again shortly after creation
            popup.after(200, lambda: popup.attributes("-topmost", True))
        except Exception:
            pass

    def _close_unified_popup(self, popup: tk.Toplevel):
        try:
            if popup.winfo_exists():
                popup.grab_release()
                popup.destroy()
        except Exception:
            pass
    
    def run(self):
        self.window.mainloop()

    # -------- Windows integration helpers --------
    def safe_notify(self, title: str, message: str, timeout: int = 10) -> None:
        try:
            icon_path = get_resource_path("icon.ico")
            notification.notify(title=title, message=message, timeout=timeout, app_name="Health & Task Reminder", app_icon=icon_path if os.path.exists(icon_path) else None)
        except Exception:
            try:
                messagebox.showinfo(title, message)
            except Exception:
                pass

    def register_startup(self, enable: bool = True) -> None:
        if _winreg is None:
            return
        try:
            run_key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            with _winreg.OpenKey(_winreg.HKEY_CURRENT_USER, run_key_path, 0, _winreg.KEY_ALL_ACCESS) as key:
                app_name = "HealthTaskReminder"
                if enable:
                    if getattr(sys, 'frozen', False):
                        exe_path = sys.executable
                    else:
                        exe_path = f'"{sys.executable}" "{os.path.abspath(__file__)}"'
                    _winreg.SetValueEx(key, app_name, 0, _winreg.REG_SZ, exe_path)
                else:
                    try:
                        _winreg.DeleteValue(key, app_name)
                    except FileNotFoundError:
                        pass
        except Exception:
            pass

if __name__ == "__main__":
    app = ReminderApp()
    app.run() 