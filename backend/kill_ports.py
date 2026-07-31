import os
import psutil
import time
import requests

def kill_port(port):
    for proc in psutil.process_iter(['pid', 'name', 'connections']):
        try:
            for conn in proc.connections(kind='inet'):
                if conn.laddr.port == port:
                    print(f"Killing process {proc.info['pid']} on port {port}")
                    proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

print("Killing 8000 and 3000...")
kill_port(8000)
kill_port(3000)
print("Done killing ports.")
