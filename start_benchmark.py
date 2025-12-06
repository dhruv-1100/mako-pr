import sys
import os
import time

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))
sys.path.append(os.path.join(os.getcwd(), 'src/rrr/pylib'))

from simplerpc import Client
from deptran.rcc_rpc import ClientControlProxy

def main():
    try:
        client = Client()
        client.connect("127.0.0.1:18100")
        proxy = ClientControlProxy(client)
        
        print("Connected to client. Sending ready block...")
        proxy.sync_client_ready_block()
        print("Client ready. Sending start...")
        proxy.sync_client_start()
        print("Client started.")
        
        while True:
            try:
                res = proxy.sync_client_response()
                # print("Got response:", res)
                if res.is_finish:
                    print("Benchmark finished.")
                    break
            except Exception as e:
                print("Error polling response:", e)
                break
            time.sleep(1)
            
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    main()
