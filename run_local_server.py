# run_local_server.py
# Attention!!!
# This script is intended to run on a local Windows machine
# that has access to the SLM, Stage hardware, and AutoHotkey.

import rpyc
from rpyc.utils.server import ThreadedServer
import numpy as np
import subprocess
import os
from hardware import SLMManager
from thorlabs_stage import ThorlabsStage
import signal
import sys

# ============== AHK Configuration ==============
AHK_EXE = r'C:\Program Files\AutoHotkey\AutoHotkey.exe'
AHK_SCRIPT_DIR = r'.\\'
AHK_CAPTURE_SCRIPT = 'capture_position.ahk'
AHK_CLICK_SCRIPT = 'click_at.ahk'
AHK_CONFIG_FILE = 'click_position.ini'


class AHKManager:
    """Local AutoHotkey script manager"""
    
    def __init__(self, ahk_exe=AHK_EXE, script_dir=AHK_SCRIPT_DIR):
        self.ahk_exe = ahk_exe
        self.script_dir = script_dir
        self.capture_script = os.path.join(script_dir, AHK_CAPTURE_SCRIPT)
        self.click_script = os.path.join(script_dir, AHK_CLICK_SCRIPT)
        self.config_file = os.path.join(script_dir, AHK_CONFIG_FILE)
        
        # Verify AHK executable exists
        if not os.path.exists(self.ahk_exe):
            print(f"⚠️ Warning: AutoHotkey not found at {self.ahk_exe}")
        else:
            print(f"✅ AHK Manager initialized")
            print(f"   AHK executable: {self.ahk_exe}")
            print(f"   Script directory: {self.script_dir}")

    def capture_position(self):
        """
        Run capture_position.ahk and read the captured coordinates.
        
        Returns:
            tuple: (x, y) coordinates, or None if capture failed
        """
        try:
            # Run capture script
            cmd = f'"{self.ahk_exe}" "{self.capture_script}"'
            print(f"🎯 Running: {cmd}")
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"❌ AHK capture script failed: {result.stderr}")
                return None
            
            # Read coordinates from config file
            if not os.path.exists(self.config_file):
                print(f"❌ Config file not found: {self.config_file}")
                return None
            
            with open(self.config_file, 'r') as f:
                lines = f.readlines()
                if len(lines) >= 2:
                    pos_x = int(float(lines[0].strip()))
                    pos_y = int(float(lines[1].strip()))
                    print(f"📍 Captured position: ({pos_x}, {pos_y})")
                    return (pos_x, pos_y)
                else:
                    print(f"❌ Invalid config file format")
                    return None
                    
        except Exception as e:
            print(f"❌ Error capturing position: {e}")
            return None

    def click_at(self, x, y):
        """
        Run click_at.ahk to click at the specified coordinates.
        
        Args:
            x: X coordinate
            y: Y coordinate
            
        Returns:
            bool: True if click was successful
        """
        try:
            cmd = f'"{self.ahk_exe}" "{self.click_script}" {x} {y}'
            print(f"🖱️ Running: {cmd}")
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"❌ AHK click script failed: {result.stderr}")
                return False
            
            print(f"✅ Clicked at ({x}, {y})")
            return True
            
        except Exception as e:
            print(f"❌ Error clicking: {e}")
            return False


class HardwareService(rpyc.Service):
    """Combined service for SLM, Stage, and AHK control"""
    
    def on_connect(self, conn):
        print("🔗 Remote connected")

    def on_disconnect(self, conn):
        print("🔌 Remote disconnected")

    # ============== SLM Functions ==============
    def exposed_upload_frame(self, data_bytes, shape, dtype_str):
        """Upload phase pattern to SLM"""
        try:
            dtype = np.dtype(dtype_str)
            array = np.frombuffer(data_bytes, dtype=dtype).reshape(shape)
            global_slm_manager.upload(array)
            return True
        except Exception as e:
            print(f"❌ SLM Error: {e}")
            return False

    # ============== Stage Functions ==============
    def exposed_stage_connect(self, stage_type=2):
        """Connect to a Thorlabs stage"""
        try:
            if stage_type not in global_stages:
                global_stages[stage_type] = ThorlabsStage(stage_type)
            
            if not global_stages[stage_type].is_connected:
                global_stages[stage_type].connect()
            
            return True
        except Exception as e:
            print(f"❌ Stage connect error: {e}")
            return False

    def exposed_stage_home(self, stage_type=2, timeout=60000):
        """Home the stage"""
        try:
            if stage_type in global_stages and global_stages[stage_type].is_connected:
                global_stages[stage_type].home(timeout)
                return True
            else:
                print(f"❌ Stage {stage_type} not connected")
                return False
        except Exception as e:
            print(f"❌ Stage home error: {e}")
            return False

    def exposed_stage_get_position(self, stage_type=2):
        """Get current position"""
        try:
            if stage_type in global_stages and global_stages[stage_type].is_connected:
                return global_stages[stage_type].get_position()
            else:
                print(f"❌ Stage {stage_type} not connected")
                return None
        except Exception as e:
            print(f"❌ Stage get_position error: {e}")
            return None

    def exposed_stage_move_to(self, position, stage_type=2, timeout=60000):
        """Move to absolute position"""
        try:
            # 确保 position 是 float 类型
            position = float(position)
            
            if stage_type in global_stages and global_stages[stage_type].is_connected:
                global_stages[stage_type].move_to(position, timeout)
                return True
            else:
                print(f"❌ Stage {stage_type} not connected")
                return False
        except Exception as e:
            print(f"❌ Stage move_to error: {e}")
            return False

    def exposed_stage_disconnect(self, stage_type=2):
        """Disconnect stage"""
        try:
            if stage_type in global_stages and global_stages[stage_type].is_connected:
                global_stages[stage_type].disconnect()
                return True
            return False
        except Exception as e:
            print(f"❌ Stage disconnect error: {e}")
            return False

    def exposed_stage_is_connected(self, stage_type=2):
        """Check if stage is connected"""
        return stage_type in global_stages and global_stages[stage_type].is_connected

    # ============== AHK Functions ==============
    def exposed_ahk_capture_position(self):
        """
        Run capture_position.ahk and return the captured coordinates.
        
        Returns:
            tuple: (x, y) coordinates, or None if capture failed
        """
        return global_ahk_manager.capture_position()

    def exposed_ahk_click_at(self, x, y):
        """
        Run click_at.ahk to click at the specified coordinates.
        
        Args:
            x: X coordinate
            y: Y coordinate
            
        Returns:
            bool: True if click was successful
        """
        return global_ahk_manager.click_at(x, y)

    def exposed_ahk_get_config(self):
        """
        Get current AHK configuration paths.
        
        Returns:
            dict: Configuration info
        """
        return {
            'ahk_exe': global_ahk_manager.ahk_exe,
            'script_dir': global_ahk_manager.script_dir,
            'capture_script': global_ahk_manager.capture_script,
            'click_script': global_ahk_manager.click_script,
            'config_file': global_ahk_manager.config_file
        }


def cleanup():
    """Clean up all hardware connections"""
    print("\n🛑 Shutting down...")
    
    # Disconnect all stages
    for stage_type, stage in global_stages.items():
        try:
            if stage.is_connected:
                stage.disconnect()
                print(f"   ✅ Stage {stage_type} disconnected")
        except:
            pass
    
    # Close SLM if needed
    try:
        if hasattr(global_slm_manager, 'close'):
            global_slm_manager.close()
            print("   ✅ SLM closed")
    except:
        pass
    
    print("👋 Goodbye!")

def signal_handler(sig, frame):
    cleanup()
    sys.exit(0)

if __name__ == "__main__":
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # kill command

    # 1. Initialize SLM hardware
    print("=" * 50)
    print("Initializing hardware components...")
    print("=" * 50)
    
    print("\n[1/3] Initializing SLM hardware...")
    global_slm_manager = SLMManager(sim_mode=False)
    
    # 2. Initialize and connect stages at startup
    print("\n[2/3] Initializing and connecting Stages...")
    global_stages = {}
    
    # Stage type definitions
    STAGE_CONFIGS = {
        1: "PRM1-Z8",   # Rotation stage
        2: "Z825B",     # Z-axis linear stage
    }
    
    # Connect both stages at startup
    for stage_type, stage_name in STAGE_CONFIGS.items():
        try:
            global_stages[stage_type] = ThorlabsStage(stage_type)
            global_stages[stage_type].connect()
            print(f"✅ Stage {stage_type} ({stage_name}) connected and ready")
        except Exception as e:
            print(f"⚠️ Warning: Failed to connect Stage {stage_type} ({stage_name}): {e}")
            print("   Stage will be available for on-demand connection")
    
    # 3. Initialize AHK manager
    print("\n[3/3] Initializing AHK manager...")
    global_ahk_manager = AHKManager()
    
    # 4. Start server
    print("\n" + "=" * 50)
    print("✅ Hardware server started, listening on port 18861...")
    print("   Available services:")
    print("   - SLM control (upload_frame)")
    print("   - Stage control (connect, home, move_to, get_position)")
    print(f"     - Stage 1: PRM1-Z8 (Rotation)")
    print(f"     - Stage 2: Z825B (Z-axis)")
    print("   - AHK control (capture_position, click_at)")
    print("=" * 50 + "\n")
    
    try:
        server = ThreadedServer(
            HardwareService, 
            port=18861, 
            hostname='127.0.0.1', 
            protocol_config={'allow_public_attrs': True}
        )
        server.start()
    except KeyboardInterrupt:
        pass
    finally:
        cleanup()
