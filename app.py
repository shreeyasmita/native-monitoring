import psutil
from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
def index():
    # use a short interval so the first call returns a meaningful value
    cpu_metric = psutil.cpu_percent(interval=0.1)
    mem_metric = psutil.virtual_memory().percent
    message = None
    if cpu_metric > 80 or mem_metric > 80:
        message = "High CPU or Memory Detected, scale up!!!"
    return render_template("index.html", cpu_metric=cpu_metric, mem_metric=mem_metric, message=message)

if __name__=='__main__':
    app.run(debug=True, host = '0.0.0.0')