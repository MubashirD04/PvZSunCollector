import tkinter as tk
from tkinter import ttk
import keyboard
import threading
import os
import sys
from sun_clicker_bot import SunClickerBot

class SunClickerGUI:
    def __init__(self, root, bot):
        self.root = root
        self.bot = bot
        self.root.title("PVZ Sun Clicker (Optimized)")
        self.root.geometry("340x520")
        self.root.resizable(False, False)
        
        # Style
        style = ttk.Style()
        style.configure("TLabel", font=("Segoe UI", 10))
        style.configure("TButton", font=("Segoe UI", 10))
        style.configure("Header.TLabel", font=("Segoe UI", 14, "bold"))
        style.configure("Status.TLabel", font=("Segoe UI", 12, "bold"))

        # Header
        ttk.Label(root, text="Sun Clicker Bot (Optimized)", style="Header.TLabel").pack(pady=10)

        # Status
        self.status_var = tk.StringVar(value="RUNNING")
        self.status_label = ttk.Label(root, textvariable=self.status_var, style="Status.TLabel", foreground="green")
        self.status_label.pack(pady=5)
        
        # Info
        self.monitor_var = tk.StringVar(value=f"Monitor: {self.bot.monitor_index}")
        ttk.Label(root, textvariable=self.monitor_var).pack(pady=2)
        
        self.templates_var = tk.StringVar(value=f"Templates: {len(self.bot.templates)}")
        ttk.Label(root, textvariable=self.templates_var).pack(pady=2)
        
        self.clicks_var = tk.StringVar(value="Clicks: 0")
        ttk.Label(root, textvariable=self.clicks_var).pack(pady=2)
        
        self.fps_var = tk.StringVar(value="FPS: 0.0")
        ttk.Label(root, textvariable=self.fps_var).pack(pady=2)

        # Controls Frame
        controls = ttk.Frame(root)
        controls.pack(pady=5, fill='x', padx=20)

        # Always on Top Checkbox
        self.always_on_top_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(controls, text="Always on Top", variable=self.always_on_top_var, 
                       command=self.toggle_topmost).pack(anchor='w', pady=5)

        # Early Exit Checkbox
        self.early_exit_var = tk.BooleanVar(value=bot.early_exit)
        ttk.Checkbutton(controls, text="Early Exit (Stop after 1st match)", 
                       variable=self.early_exit_var, 
                       command=self.toggle_early_exit).pack(anchor='w', pady=5)

        # Confidence Threshold
        ttk.Label(controls, text="Confidence Threshold:").pack(anchor='w', pady=(10,0))
        self.confidence_var = tk.DoubleVar(value=bot.confidence_threshold)
        confidence_scale = ttk.Scale(controls, from_=0.5, to=0.95, variable=self.confidence_var, 
                                    orient='horizontal', command=self.update_confidence)
        confidence_scale.pack(fill='x', pady=2)
        self.confidence_label = ttk.Label(controls, text=f"{bot.confidence_threshold:.2f}")
        self.confidence_label.pack(anchor='w')

        ttk.Separator(controls, orient='horizontal').pack(fill='x', pady=10)

        ttk.Button(controls, text="Toggle Pause (P)", command=self.toggle_pause).pack(fill='x', pady=2)
        ttk.Button(controls, text="Next Monitor (M)", command=self.cycle_monitor).pack(fill='x', pady=2)
        ttk.Button(controls, text="Enable Debug View (D)", command=self.toggle_debug).pack(fill='x', pady=2)
        ttk.Button(controls, text="Quit (Q)", command=self.quit_app).pack(fill='x', pady=2)

        # Footer
        ttk.Label(root, text="Hotkeys: P (Pause), M (Monitor), D (Debug), Q (Quit)", 
                 font=("Segoe UI", 8)).pack(side='bottom', pady=5)

        # Register callbacks
        self.bot.callback_update_ui = self.update_ui_from_thread
        
        # Update info periodically
        self.update_info()

    def update_info(self):
        self.clicks_var.set(f"Clicks: {self.bot.clicks_counter}")
        self.templates_var.set(f"Templates: {len(self.bot.templates)}")
        
        # Calculate and display FPS
        if self.bot.fps_counter:
            avg_fps = 1.0 / (sum(self.bot.fps_counter) / len(self.bot.fps_counter))
            self.fps_var.set(f"FPS: {avg_fps:.1f}")
        
        self.root.after(500, self.update_info)

    def toggle_topmost(self):
        self.root.attributes('-topmost', self.always_on_top_var.get())

    def toggle_early_exit(self):
        self.bot.early_exit = self.early_exit_var.get()
        print(f"Early exit: {'ON' if self.bot.early_exit else 'OFF'}")

    def toggle_debug(self):
        self.bot.headless = not self.bot.headless
        status = "disabled" if self.bot.headless else "enabled"
        print(f"Debug view {status}")

    def update_confidence(self, value):
        self.bot.confidence_threshold = float(value)
        self.confidence_label.config(text=f"{float(value):.2f}")

    def toggle_pause(self):
        self.bot.toggle_pause()
        self.update_ui()

    def cycle_monitor(self):
        self.bot.cycle_monitor()
        self.update_ui()

    def quit_app(self):
        cleanup()

    def update_ui(self):
        if self.bot.paused:
            self.status_var.set("PAUSED")
            self.status_label.configure(foreground="red")
        else:
            self.status_var.set("RUNNING")
            self.status_label.configure(foreground="green")
        
        self.monitor_var.set(f"Monitor: {self.bot.monitor_index}")

    def update_ui_from_thread(self):
        self.root.after(0, self.update_ui)

def cleanup():
    print("Shutting down...")
    bot.stop()
    root.destroy()
    os._exit(0)

if __name__ == "__main__":
    root = tk.Tk()
    
    # Initialize Bot
    print("Initializing bot...")
    bot = SunClickerBot()
    
    # Initialize GUI
    print("Initializing GUI...")
    gui = SunClickerGUI(root, bot)
    
    # Start Bot Thread
    bot.start()

    keyboard.add_hotkey('p', bot.toggle_pause)
    keyboard.add_hotkey('m', bot.cycle_monitor)
    keyboard.add_hotkey('d', gui.toggle_debug)
    keyboard.add_hotkey('q', cleanup)
    
    root.protocol("WM_DELETE_WINDOW", cleanup)
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        cleanup()
    finally:
        keyboard.unhook_all_hotkeys()
