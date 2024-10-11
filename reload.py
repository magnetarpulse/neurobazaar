import time
import subprocess
import sys
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class ServerReloader(FileSystemEventHandler):
    def __init__(self):
        self.process = None
        self.start_server()

    def start_server(self):
        if self.process:
            self.process.terminate()
            self.process.wait()
        self.process = subprocess.Popen([sys.executable, 'maxslices+original_images.py'])

    def on_modified(self, event):
        if event.src_path.endswith('maxslices+original_images.py'):
            print("Detected change in maxslices+original_images.py. Restarting...")
            self.start_server()

if __name__ == "__main__":
    event_handler = ServerReloader()
    observer = Observer()
    observer.schedule(event_handler, path='.', recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
