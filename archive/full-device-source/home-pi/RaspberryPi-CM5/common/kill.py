#!/usr/bin/env python3
import os,sys,time,subprocess

USER = "pi" 
HOME = f"/home/{USER}"

def kill_processes():
   
    try:
        subprocess.run(
            ["sudo", "-u", USER, "pkill", "-f", "python.*main.py"],
            check=True
        )
        subprocess.run(
            ["sudo", "-u", USER, "pkill", "-f", "python.*demoen.py"],
            check=True
        )
    except subprocess.CalledProcessError:
        pass 

if __name__ == "__main__":
    kill_processes()
    time.sleep(1)
    os.system(f"nohup {sys.executable} ./common/main.py > /dev/null 2>&1 &")