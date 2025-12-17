# run_local_server.py
# Attention!!!
# This script is intended to run on a local Windows machine
# that has access to the SLM hardware.

import rpyc
from rpyc.utils.server import ThreadedServer
import numpy as np
from hardware import SLMManager 

class SLMService(rpyc.Service):
    def on_connect(self, conn):
        print("🔗 Remote connected")

    def on_disconnect(self, conn):
        print("🔌 Remote disconnected")

    # Functions exposed for remote calls 
    # must start with exposed_
    def exposed_upload_frame(self, data_bytes, shape, dtype_str):
        """
        Receive byte stream from remote
        convert back to numpy array, and upload to hardware
        """
        try:
            # 1. deserialize: bytes -> Numpy
            dtype = np.dtype(dtype_str)
            array = np.frombuffer(data_bytes, dtype=dtype).reshape(shape)
            
            # 2. call the actual hardware interface
            # Note: slm_manager is globally initialized, only once
            global_slm_manager.upload(array)
            return True
        except Exception as e:
            print(f"❌ Error: {e}")
            return False

if __name__ == "__main__":
    # 1. initialize SLM hardware
    print("Initializing SLM hardware...")
    global_slm_manager = SLMManager(sim_mode=False) 
    
    # 2. start server listening on port 18861
    print("✅ SLM server started, listening on port 18861...")
    server = ThreadedServer(SLMService, port=18861, hostname='127.0.0.1', protocol_config={'allow_public_attrs': True})
    server.start()