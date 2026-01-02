import cv2
import numpy as np
import pyautogui
import time
import keyboard
import os
import mss
from PIL import Image

def main():
    print("PVZ Sun Autoclicker with Debug View started.")
    print("Press 'q' to quit.")
    
    # Path to the sun image
    sun_image_path = 'sun.png'
    
    if not os.path.exists(sun_image_path):
        print(f"Error: {sun_image_path} not found in the current directory.")
        return

    # Load template image
    template = cv2.imread(sun_image_path, cv2.IMREAD_COLOR)
    if template is None:
        print("Error: Could not load image with OpenCV.")
        return
        
    template_h, template_w = template.shape[:2]
    
    # State for clicking logic
    waiting_for_sun = False
    sun_detection_start_time = 0
    
    # Use a dictionary for mutable state in closures/callbacks
    state = {'paused': False, 'running': True, 'monitor_index': 1}

    # Initialize MSS early so we can access it in callbacks
    sct = mss.mss()

    def cycle_monitor():
        num_monitors = len(sct.monitors)
        if num_monitors <= 2: # monitors[0] is all, monitors[1] is prim. Need at least monitors[2] to cycle
             pass
        
        # Cycle index: 1 -> 2 -> ... -> (len-1) -> 1
        new_index = state['monitor_index'] + 1
        if new_index >= num_monitors:
            new_index = 1
            
        state['monitor_index'] = new_index
        print(f"Switched to Monitor {new_index}")
    
    def toggle_pause():
        state['paused'] = not state['paused']
        status = "PAUSED" if state['paused'] else "RESUMED"
        print(f"\n{status}")

    def quit_program():
        state['running'] = False
        print("\nExiting...")

    # Set up non-blocking hotkeys
    keyboard.add_hotkey('p', toggle_pause)
    keyboard.add_hotkey('m', cycle_monitor)
    keyboard.add_hotkey('q', quit_program)
    
    print("Commands: 'p' to pause, 'm' to cycle monitor, 'q' to quit")
    
    CONFIDENCE_THRESHOLD = 0.75
    CLICK_DELAY = 0.0 

    cv2.namedWindow("PVZ Bot View", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("PVZ Bot View", 960, 540)

    # Initialize MSS
    # sct initialized above
    
    # Get the primary monitor (or the one covering the game)
    # Monitor selection happens inside loop based on state['monitor_index']

    try:
        while state['running']:
            # Get current monitor
            monitor = sct.monitors[state['monitor_index']]

            # 1. Capture screen using MSS
            # grab() returns a raw MSS image
            sct_img = sct.grab(monitor)
            
            # Convert to numpy array
            # MSS returns BGRA. OpenCV uses BGR.
            # We can use it directly as BGR if we ignore Alpha, 
            # or convert explicitly.
            frame_bgra = np.array(sct_img)
            frame_bgr = cv2.cvtColor(frame_bgra, cv2.COLOR_BGRA2BGR)
            
            if state['paused']:
                cv2.putText(frame_bgr, "PAUSED (Press 'p' to resume)", (50, 50), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            else:
                # 2. Template Matching
                res = cv2.matchTemplate(frame_bgr, template, cv2.TM_CCOEFF_NORMED)
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
                
                # 3. Logic & Visualization
                if max_val >= CONFIDENCE_THRESHOLD:
                    # Sun found
                    top_left = max_loc
                    bottom_right = (top_left[0] + template_w, top_left[1] + template_h)
                    
                    # Draw box
                    cv2.rectangle(frame_bgr, top_left, bottom_right, (0, 255, 0), 2)
                    
                    # Draw confidence text
                    text = f"Sun: {max_val:.2f}"
                    cv2.putText(frame_bgr, text, (top_left[0], top_left[1] - 10), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

                    # Click Logic
                    center_x = top_left[0] + template_w // 2
                    # Note: MSS captures relative to monitor. 
                    # If using multiple monitors, pyautogui.click needs absolute coords.
                    # top_left is relative to 'monitor' top-left.
                    # monitor['top'] and monitor['left'] give offsets.
                    abs_x = monitor['left'] + center_x
                    abs_y = monitor['top'] + top_left[1] + template_h // 2
                    
                    pyautogui.click(abs_x, abs_y)
                    
                    # Small sleep to allow game to register click
                    time.sleep(0.05) 
                    
                else:
                    waiting_for_sun = False

            # Show the debug window
            display_frame = cv2.resize(frame_bgr, (0, 0), fx=0.5, fy=0.5)
            cv2.imshow("PVZ Bot View", display_frame)
            
            # Check OpenCV window key (backup for 'q')
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
    finally:
        keyboard.unhook_all_hotkeys()
        cv2.destroyAllWindows()
        print("Cleaned up windows.")

if __name__ == "__main__":
    main()
