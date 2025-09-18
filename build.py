import PyInstaller.__main__
import os

# Get the current directory
current_dir = os.path.dirname(os.path.abspath(__file__))

# Define the path to the main script
main_script = os.path.join(current_dir, "hydration_reminder.py")

# Define the path to the assets directory
assets_dir = os.path.join(current_dir, "assets")

# Create the assets directory if it doesn't exist
os.makedirs(assets_dir, exist_ok=True)

# Define PyInstaller arguments (icon argument removed)
pyinstaller_args = [
    main_script,
    "--onefile",
    "--windowed",
    "--name=HydrationReminder",
    "--add-data=assets;assets",
    "--hidden-import=customtkinter",
    "--hidden-import=PIL",
    "--hidden-import=plyer",
    "--hidden-import=tkcalendar",
    "--hidden-import=pystray",
    "--hidden-import=json",
    "--hidden-import=threading",
    "--hidden-import=datetime",
    "--hidden-import=time",
    "--hidden-import=os",
    "--hidden-import=tkinter",
    "--hidden-import=ttk",
    "--clean",
    "--noconfirm"
]

# Run PyInstaller
PyInstaller.__main__.run(pyinstaller_args) 