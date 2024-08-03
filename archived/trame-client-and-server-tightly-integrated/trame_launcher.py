import subprocess
import os
import signal
import argparse

processes = []

def start_instance(port):
    """Start an instance of the app on the specified port."""
    process = subprocess.Popen(["python3.12", "updated_test_app.py", "--port", str(port)])
    processes.append(process)
    print(f"Started instance on port {port}")

def stop_instances():
    """Stop all running instances."""
    for process in processes:
        os.kill(process.pid, signal.SIGTERM)
        print(f"Stopped instance with PID {process.pid}")

def main():
    parser = argparse.ArgumentParser(description="Launcher for multi-user instances.")
    parser.add_argument("--num-instances", type=int, default=1, help="Number of instances to start.")
    parser.add_argument("--start-port", type=int, default=5454, help="Starting port for instances.")
    args = parser.parse_args()

    try:
        for i in range(args.num_instances):
            port = args.start_port + i
            start_instance(port)
        
        print("Press Ctrl+C to stop all instances.")
        while True:
            pass

    except KeyboardInterrupt:
        print("\nStopping all instances...")
        stop_instances()

if __name__ == "__main__":
    main()