import subprocess
import threading
import logging
import queue
import sys

if sys.version_info < (3, 0):
    sys.stdout.write("Sorry, requires Python 3.x, not Python 2.x\n")
    sys.exit(1)

def ps(hosts, grep_filter):
    output = []
    q = queue.Queue(len(hosts))

    def work(host, grep_filter):
        cmd = ['/bin/bash', '-c', "ps -eLF | grep \"{}\"".format(grep_filter)]
        if host in ["localhost", "127.0.0.1"]:
            final_cmd = cmd
        else:
            ssh_cmd = ['ssh', host]
            ssh_cmd.extend(['/bin/bash', '-c', "'ps -eLF | grep \"{}\"'".format(grep_filter)])
            final_cmd = ssh_cmd
            
        output = ""
        output += "----------\nServer: {}\n-------------\n".format(host)

        try:
            o = subprocess.check_output(final_cmd)
            output += str(o)
        except subprocess.CalledProcessError as e:
            output += "error calling ps! returncode {}".format(e.returncode)
            # sys.exit(1) # Don't exit on error, just log it
        q.put(output)


    threads=[]
    for host in hosts:
        t = threading.Thread(target=work, args=(host, grep_filter,))
        threads.append(t)
        t.start()

    for x in range(len(hosts)):
        try:
            output.append(q.get(True, 1))
        except queue.Empty as e:
            logging.debug("timeout waiting for value from: " + str(x))
            pass

    return '\n'.join(output)


def killall(hosts, proc, param="-9"):
    def work(host, proc, param):
        cmd = ['killall', '-q', param, proc]
        if host in ["localhost", "127.0.0.1"]:
            final_cmd = cmd
        else:
            ssh_cmd = ['ssh', host]
            ssh_cmd.extend(cmd)
            final_cmd = ssh_cmd
            
        res = subprocess.call(final_cmd)
        if res != 0:
            logging.error("host: {}; killall did not kill anything".format(host))

    threads=[]
    for host in hosts:
        t = threading.Thread(target=work,args=(host, proc, param,))
        threads.append(t)
        t.start()

    logging.info("waiting for killall commands to finish.")
    for t in threads:
        t.join()
    logging.info("done waiting for killall commands to finish.")
