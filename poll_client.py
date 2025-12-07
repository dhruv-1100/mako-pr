import time
import sys
import os
from simplerpc import Client
from src.deptran.rcc_rpc import ClientControlProxy

def poll():
    client = Client()
    client.connect("127.0.0.1:19100")
    proxy = ClientControlProxy(client)
    
    print("Calling client_start...")
    proxy.sync_client_start()
    print("client_start returned.")
    
    for i in range(10):
        print(f"Polling {i}...")
        try:
            future = proxy.async_client_response()
            res = future.result
            print(f"Result: is_finish={res.is_finish}")
            time.sleep(1)
        except Exception as e:
            print(f"Error: {e}")
            break

if __name__ == "__main__":
    poll()
