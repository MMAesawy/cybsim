import pandas as pd
import subprocess
import sys

def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

req = pd.read_csv("env.txt").iloc[:,0].tolist()
new_req = []
for r in req:
    try:
        install(r)
        new_req.append(r)
        print("Installed %s" % r)
    except:
        print("Error installing %s" % r)

pd.DataFrame(new_req).to_csv("req.txt", index=False, header=False)