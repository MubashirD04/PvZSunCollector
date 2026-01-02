import cv2
import numpy as np
import pyautogui
import time
import keyboard
import os
import mss
import threading
import tkinter as tk
from tkinter import ttk

class SunClickerBot:
    def __init__(self, callback_update_ui=None):
        self.running = False
        self.paused = False
        self.monitor_index = 1
        self.sun_image_path = 'sun.png'
        self.headless = True
        self.confidence_threshold = 0.75
        self.callback_update_ui = callback_update_ui
        self.lock = threading.Lock()
        
        # Load resources
        self.load_template()

    def load_template(self):
        if not os.path.exists(self.sun_image_path):
            print(f"Error: {self.sun_image_path} not found.")
            return

        self.template = cv2.imread(self.sun_image_path, cv2.IMREAD_COLOR)
        if self.template is None:
            print("Error: Could not load image with OpenCV.")
        else:
            self.template_h, self.template_w = self.template.shape[:2]

    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self.run_loop, daemon=True)
            self.thread.start()
            print("Bot started.")

    def stop(self):
        self.running = False
        if hasattr(self, 'thread'):
            self.thread.join(timeout=1.0)
        print("Bot stopped.")

    def toggle_pause(self):
        with self.lock:
            self.paused = not self.paused
        status = "PAUSED" if self.paused else "RUNNING"
        print(f"Bot State: {status}")
        if self.callback_update_ui:
            self.callback_update_ui()

    def cycle_monitor(self):
        with mss.mss() as sct:
            num_monitors = len(sct.monitors)
            if num_monitors <= 2:
                return

            with self.lock:
                new_index = self.monitor_index + 1
                if new_index >= num_monitors:
                    new_index = 1
                self.monitor_index = new_index
            
        print(f"Switched to Monitor {self.monitor_index}")
        if self.callback_update_ui:
            self.callback_update_ui()

    def run_loop(self):
        if not self.headless:
            cv2.namedWindow("PVZ Bot View", cv2.WINDOW_NORMAL)
            cv2.resizeWindow("PVZ Bot View", 960, 540)

        with mss.mss() as sct:
            try:
                while self.running:
                    if self.template is None:
                        time.sleep(1)
                        continue

                    with self.lock:
                        current_monitor_idx = self.monitor_index
                        is_paused = self.paused

                    monitor = sct.monitors[current_monitor_idx]
                    sct_img = sct.grab(monitor)
                    frame_bgra = np.array(sct_img)
                    frame_bgr = cv2.cvtColor(frame_bgra, cv2.COLOR_BGRA2BGR)

                    if is_paused:
                        cv2.putText(frame_bgr, "PAUSED", (50, 50), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                    else:
                        res = cv2.matchTemplate(frame_bgr, self.template, cv2.TM_CCOEFF_NORMED)
                        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

                        if max_val >= self.confidence_threshold:
                            top_left = max_loc
                            bottom_right = (top_left[0] + self.template_w, top_left[1] + self.template_h)
                            
                            # Visualization
                            cv2.rectangle(frame_bgr, top_left, bottom_right, (0, 255, 0), 2)
                            cv2.putText(frame_bgr, f"Sun: {max_val:.2f}", (top_left[0], top_left[1] - 10), 
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

                            # Click Logic
                            center_x = top_left[0] + self.template_w // 2
                            abs_x = monitor['left'] + center_x
                            abs_y = monitor['top'] + top_left[1] + self.template_h // 2
                            
                            pyautogui.click(abs_x, abs_y)
                            time.sleep(0.05) 

                    if not self.headless:
                        display_frame = cv2.resize(frame_bgr, (0, 0), fx=0.5, fy=0.5)
                        cv2.imshow("PVZ Bot View", display_frame)
                        if cv2.waitKey(1) & 0xFF == ord('q'):
                            self.running = False
                            break
            finally:
                if not self.headless:
                    cv2.destroyAllWindows()

class SunClickerGUI:
    def __init__(self, root, bot):
        self.root = root
        self.bot = bot
        self.root.title("PVZ Sun Clicker")
        self.root.geometry("300x260")
        self.root.resizable(False, False)
        
        # Style
        style = ttk.Style()
        style.configure("TLabel", font=("Segoe UI", 10))
        style.configure("TButton", font=("Segoe UI", 10))
        style.configure("Header.TLabel", font=("Segoe UI", 14, "bold"))
        style.configure("Status.TLabel", font=("Segoe UI", 12, "bold"))

        # Header
        ttk.Label(root, text="Sun Clicker Bot", style="Header.TLabel").pack(pady=10)

        # Status
        self.status_var = tk.StringVar(value="RUNNING")
        self.status_label = ttk.Label(root, textvariable=self.status_var, style="Status.TLabel", foreground="green")
        self.status_label.pack(pady=5)

        # Monitor Info
        self.monitor_var = tk.StringVar(value=f"Monitor: {self.bot.monitor_index}")
        ttk.Label(root, textvariable=self.monitor_var).pack(pady=5)

        # Controls Frame
        controls = ttk.Frame(root)
        controls.pack(pady=10, fill='x', padx=20)

        ttk.Button(controls, text="Toggle Pause (P)", command=self.toggle_pause).pack(fill='x', pady=2)
        ttk.Button(controls, text="Next Monitor (M)", command=self.cycle_monitor).pack(fill='x', pady=2)
        ttk.Button(controls, text="Quit (Q)", command=self.quit_app).pack(fill='x', pady=2)

        # Footer
        ttk.Label(root, text="Hotkeys: P (Pause), M (Monitor), Q (Quit)", font=("Segoe UI", 8)).pack(side='bottom', pady=5)

        # Register callbacks
        self.bot.callback_update_ui = self.update_ui_from_thread

    def toggle_pause(self):
        self.bot.toggle_pause()
        self.update_ui()

    def cycle_monitor(self):
        self.bot.cycle_monitor()
        self.update_ui()

    def quit_app(self):
        cleanup()

    def update_ui(self):
        # Update Status
        if self.bot.paused:
            self.status_var.set("PAUSED")
            self.status_label.configure(foreground="red")
        else:
            self.status_var.set("RUNNING")
            self.status_label.configure(foreground="green")
        
        # Update Monitor
        self.monitor_var.set(f"Monitor: {self.bot.monitor_index}")

    def update_ui_from_thread(self):
        # Schedule update on main thread
        self.root.after(0, self.update_ui)

def cleanup():
    print("Shutting down...")
    bot.stop()
    root.destroy()
    os._exit(0) # Force exit to kill any hanging threads

if __name__ == "__main__":
    root = tk.Tk()
    
    # Initialize Bot
    bot = SunClickerBot()
    
    # Initialize GUI
    gui = SunClickerGUI(root, bot)
    
    # Start Bot Thread
    bot.start()

    # global hooks for hotkeys need to interact with the bot/gui
    # We use lambda to call the GUI methods which are thread-safe-ish (update_ui schedules on main)
    # or directly call bot methods which trigger callback.
    # Calling bot.toggle_pause() triggers callback -> gui.update_ui_from_thread -> root.after -> gui.update_ui
    keyboard.add_hotkey('p', bot.toggle_pause)
    keyboard.add_hotkey('m', bot.cycle_monitor)
    keyboard.add_hotkey('q', cleanup)
    
    # Handle window close button
    root.protocol("WM_DELETE_WINDOW", cleanup)
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        cleanup()
    finally:
        keyboard.unhook_all_hotkeys()

