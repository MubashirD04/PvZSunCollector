import cv2
import numpy as np
import pyautogui
import time
import os
import mss
import threading
import glob
from concurrent.futures import ThreadPoolExecutor, as_completed
import sys
from collections import deque

def resource_path(relative_path):
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

class SunClickerBot:
    def __init__(self, callback_update_ui=None):
        self.running = False
        self.paused = False
        self.monitor_index = 1
        self.sun_images_dir = resource_path('resources')  # Look in resources directory
        self.headless = True
        self.confidence_threshold = 0.70
        self.callback_update_ui = callback_update_ui
        self.lock = threading.Lock()
        
        # Multiple templates support
        self.templates = []  # List of template dicts
        
        self.click_cooldown = 0.05
        self.last_click_time = 0
        self.click_positions = deque(maxlen=10)
        self.duplicate_threshold = 30
        
        self.frame_skip = 2  # Process every 2nd frame
        self.frame_counter = 0
        
        self.downscale_factor = 0.75  # Process at 75% size, 44% faster
        
        self.early_exit = True
        
        self.use_roi = False
        self.roi = None  # (x, y, w, h) - set this to game window area if known
        
        self.use_parallel = True
        self.thread_pool = ThreadPoolExecutor(max_workers=3)
        
        self.use_multiscale = False
        self.scales = [1.0]
        
        # Performance metrics
        self.fps_counter = deque(maxlen=30)
        self.clicks_counter = 0
        self.detections_by_template = {}
        self.template_priorities = {}  # Track performance to prioritize templates
        
        # Load all templates
        self.load_templates()

    def load_templates(self):
        patterns = [
            'sun.png',
            'sun*.png',
            'Sun*.png',
            'SUN*.png'
        ]
        
        template_files = []
        for pattern in patterns:
            files = glob.glob(os.path.join(self.sun_images_dir, pattern))
            template_files.extend(files)
        
        # Remove duplicates
        template_files = list(set(template_files))
        
        if not template_files:
            print("Error: No sun template images found!")
            print(f"Looking in: {self.sun_images_dir}")
            print("Please add sun.png, sun1.png, sun2.png, etc.")
            return
        
        print(f"Found {len(template_files)} template image(s):")
        
        for filepath in template_files:
            template_bgr = cv2.imread(filepath, cv2.IMREAD_COLOR)
            if template_bgr is None:
                print(f"  [X] Failed to load: {os.path.basename(filepath)}")
                continue
            
            # OPTIMIZATION: Preprocess templates at multiple scales
            template_gray = cv2.cvtColor(template_bgr, cv2.COLOR_BGR2GRAY)
            
            # OPTIMIZATION: Pre-downscale template to match processing scale
            if self.downscale_factor != 1.0:
                template_gray_scaled = cv2.resize(template_gray, None, 
                                                  fx=self.downscale_factor, 
                                                  fy=self.downscale_factor,
                                                  interpolation=cv2.INTER_AREA)
            else:
                template_gray_scaled = template_gray
            
            h, w = template_gray_scaled.shape[:2]
            name = os.path.basename(filepath)
            
            self.templates.append({
                'bgr': template_bgr,
                'gray': template_gray_scaled,  # Use scaled version
                'name': name,
                'width': w,
                'height': h,
                'priority': 0  # Will be updated based on success rate
            })
            
            self.detections_by_template[name] = 0
            self.template_priorities[name] = 0
            print(f"  [+] Loaded: {name} ({w}x{h})")
        
        if not self.templates:
            print("Error: No valid template images could be loaded!")
        else:
            print(f"\nTotal templates loaded: {len(self.templates)}")
            print(f"Optimizations enabled:")
            print(f"  - Downscale factor: {self.downscale_factor}")
            print(f"  - Frame skip: {self.frame_skip}")
            print(f"  - Early exit: {self.early_exit}")
            print(f"  - Parallel processing: {self.use_parallel}")

    def match_template_worker(self, frame_gray, template_info):
        #Worker function for parallel template matching
        try:
            result = cv2.matchTemplate(frame_gray, template_info['gray'], cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            if max_val >= self.confidence_threshold:
                return {
                    'found': True,
                    'confidence': max_val,
                    'location': max_loc,
                    'template': template_info['name'],
                    'width': template_info['width'],
                    'height': template_info['height']
                }
        except Exception as e:
            print(f"Error matching template {template_info['name']}: {e}")
        
        return {'found': False}

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
        
        # Cleanup thread pool
        if self.use_parallel:
            self.thread_pool.shutdown(wait=False)
        
        print("Bot stopped.")
        
        # Print detection stats
        if self.detections_by_template:
            print("\n=== Detection Statistics ===")
            for name, count in sorted(self.detections_by_template.items(), key=lambda x: x[1], reverse=True):
                print(f"  {name}: {count} detections")

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

    def is_duplicate_click(self, x, y):
        # Check if we recently clicked near this position
        for prev_x, prev_y, prev_time in self.click_positions:
            distance = np.sqrt((x - prev_x)**2 + (y - prev_y)**2)
            if distance < self.duplicate_threshold and (time.time() - prev_time) < 0.5:
                return True
        return False

    def run_loop(self):
        window_created = False
        
        with mss.mss() as sct:
            try:
                while self.running:
                    frame_start = time.time()
                    
                    if not self.templates:
                        time.sleep(1)
                        continue

                    self.frame_counter += 1
                    if self.frame_counter % self.frame_skip != 0:
                        time.sleep(0.001)
                        continue

                    with self.lock:
                        current_monitor_idx = self.monitor_index
                        is_paused = self.paused
                        headless_mode = self.headless

                    # Window management
                    if not headless_mode and not window_created:
                        cv2.namedWindow("PVZ Bot View", cv2.WINDOW_NORMAL)
                        cv2.resizeWindow("PVZ Bot View", 960, 540)
                        window_created = True
                    elif headless_mode and window_created:
                        cv2.destroyWindow("PVZ Bot View")
                        window_created = False

                    monitor = sct.monitors[current_monitor_idx]
                    sct_img = sct.grab(monitor)
                    
                    # Convert to numpy array and BGR
                    frame_bgra = np.array(sct_img)
                    frame_bgr = cv2.cvtColor(frame_bgra, cv2.COLOR_BGRA2BGR)

                    if is_paused:
                        if not headless_mode:
                            cv2.putText(frame_bgr, "PAUSED", (50, 50), 
                                      cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                    else:
                        if self.downscale_factor != 1.0:
                            frame_gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
                            frame_gray = cv2.resize(frame_gray, None, 
                                                   fx=self.downscale_factor, 
                                                   fy=self.downscale_factor,
                                                   interpolation=cv2.INTER_AREA)
                        else:
                            frame_gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
                        
                        if self.use_roi and self.roi:
                            x, y, w, h = self.roi
                            frame_gray = frame_gray[y:y+h, x:x+w]
                        
                        sorted_templates = sorted(self.templates, 
                                                key=lambda t: self.template_priorities.get(t['name'], 0), 
                                                reverse=True)
                        
                        best_matches = []

                        if self.use_parallel and len(sorted_templates) > 2:
                            # Parallel processing for multiple templates
                            futures = []
                            for template_info in sorted_templates:
                                future = self.thread_pool.submit(
                                    self.match_template_worker, 
                                    frame_gray, 
                                    template_info
                                )
                                futures.append(future)
                            
                            for future in as_completed(futures):
                                result = future.result()
                                if result['found']:
                                    best_matches.append(result)
                                    if self.early_exit:
                                        break
                        else:
                            # Sequential processing (faster for 1-2 templates)
                            for template_info in sorted_templates:
                                result = self.match_template_worker(frame_gray, template_info)
                                if result['found']:
                                    best_matches.append(result)
                                    if self.early_exit:
                                        break
                        
                        # Sort by confidence and click
                        best_matches.sort(key=lambda x: x['confidence'], reverse=True)
                        
                        for match in best_matches[:5]:  # Process top 5 matches max
                            current_time = time.time()
                            
                            if current_time - self.last_click_time < self.click_cooldown:
                                break
                            
                            scale_factor = 1.0 / self.downscale_factor
                            center_x = int((match['location'][0] + match['width'] // 2) * scale_factor)
                            center_y = int((match['location'][1] + match['height'] // 2) * scale_factor)
                            
                            # Adjust for ROI offset if used
                            if self.use_roi and self.roi:
                                center_x += self.roi[0]
                                center_y += self.roi[1]
                            
                            abs_x = monitor['left'] + center_x
                            abs_y = monitor['top'] + center_y
                            
                            if self.is_duplicate_click(abs_x, abs_y):
                                continue
                            
                            # Click
                            pyautogui.click(abs_x, abs_y)
                            self.clicks_counter += 1
                            self.detections_by_template[match['template']] += 1
                            
                            self.template_priorities[match['template']] = self.template_priorities.get(match['template'], 0) + 1
                            
                            # Record click
                            self.click_positions.append((abs_x, abs_y, current_time))
                            self.last_click_time = current_time
                            
                            print(f"Clicked sun at ({abs_x}, {abs_y}) - {match['template']} - conf: {match['confidence']:.3f}")
                            
                            if not headless_mode:
                                box_x = int(match['location'][0] * scale_factor)
                                box_y = int(match['location'][1] * scale_factor)
                                box_w = int(match['width'] * scale_factor)
                                box_h = int(match['height'] * scale_factor)
                                
                                color = (0, 255, 0) if 'sun.png' in match['template'] else (255, 0, 255)
                                cv2.rectangle(frame_bgr, 
                                            (box_x, box_y), 
                                            (box_x + box_w, box_y + box_h), 
                                            color, 2)
                                cv2.putText(frame_bgr, 
                                          f"{match['confidence']:.2f}", 
                                          (box_x, box_y - 10), 
                                          cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                            
                            time.sleep(0.02)

                    frame_time = time.time() - frame_start
                    self.fps_counter.append(frame_time)
                    
                    if not headless_mode:
                        # Display stats
                        avg_fps = 1.0 / (sum(self.fps_counter) / len(self.fps_counter)) if self.fps_counter else 0
                        cv2.putText(frame_bgr, f"FPS: {avg_fps:.1f} | Clicks: {self.clicks_counter}", 
                                  (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
                        cv2.putText(frame_bgr, f"Templates: {len(self.templates)} | Skip: {self.frame_skip} | Scale: {self.downscale_factor}", 
                                  (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
                        
                        display_frame = cv2.resize(frame_bgr, (0, 0), fx=0.5, fy=0.5)
                        cv2.imshow("PVZ Bot View", display_frame)
                        if cv2.waitKey(1) & 0xFF == ord('q'):
                            self.running = False
                            break
                    
                    time.sleep(0.001)
                    
            finally:
                if window_created:
                    cv2.destroyAllWindows()
