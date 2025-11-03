from flask import Flask, jsonify, Response
import psutil
import json
from datetime import datetime
import platform

class CloudNativeMonitor:
    def __init__(self):
        self.start_time = datetime.now()
    
    def get_cpu_info(self):
        """Get detailed CPU metrics"""
        return {
            'percent': psutil.cpu_percent(interval=1),
            'count': psutil.cpu_count(),
            'count_logical': psutil.cpu_count(logical=True),
            'frequency': psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None,
            'per_cpu': psutil.cpu_percent(interval=1, percpu=True)
        }
    
    def get_memory_info(self):
        """Get memory metrics"""
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        return {
            'virtual': {
                'total': mem.total,
                'available': mem.available,
                'used': mem.used,
                'percent': mem.percent,
                'total_gb': round(mem.total / (1024**3), 2),
                'used_gb': round(mem.used / (1024**3), 2),
                'available_gb': round(mem.available / (1024**3), 2)
            },
            'swap': {
                'total': swap.total,
                'used': swap.used,
                'percent': swap.percent,
                'total_gb': round(swap.total / (1024**3), 2),
                'used_gb': round(swap.used / (1024**3), 2)
            }
        }
    
    def get_disk_info(self):
        """Get disk metrics"""
        partitions = []
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                partitions.append({
                    'device': partition.device,
                    'mountpoint': partition.mountpoint,
                    'fstype': partition.fstype,
                    'total_gb': round(usage.total / (1024**3), 2),
                    'used_gb': round(usage.used / (1024**3), 2),
                    'free_gb': round(usage.free / (1024**3), 2),
                    'percent': usage.percent
                })
            except PermissionError:
                continue
        
        disk_io = psutil.disk_io_counters()
        return {
            'partitions': partitions,
            'io': {
                'read_bytes': disk_io.read_bytes,
                'write_bytes': disk_io.write_bytes,
                'read_mb': round(disk_io.read_bytes / (1024**2), 2),
                'write_mb': round(disk_io.write_bytes / (1024**2), 2)
            } if disk_io else None
        }
    
    def get_network_info(self):
        """Get network metrics"""
        net_io = psutil.net_io_counters()
        connections = len(psutil.net_connections())
        
        return {
            'io': {
                'bytes_sent': net_io.bytes_sent,
                'bytes_recv': net_io.bytes_recv,
                'mb_sent': round(net_io.bytes_sent / (1024**2), 2),
                'mb_recv': round(net_io.bytes_recv / (1024**2), 2),
                'packets_sent': net_io.packets_sent,
                'packets_recv': net_io.packets_recv
            },
            'connections': connections
        }
    
    def get_system_info(self):
        """Get system information"""
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.now() - boot_time
        
        return {
            'hostname': platform.node(),
            'system': platform.system(),
            'release': platform.release(),
            'version': platform.version(),
            'machine': platform.machine(),
            'processor': platform.processor(),
            'boot_time': boot_time.isoformat(),
            'uptime_seconds': uptime.total_seconds(),
            'uptime_human': str(uptime).split('.')[0]
        }
    
    def get_process_info(self):
        """Get top processes by CPU and memory"""
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # Sort by CPU usage
        top_cpu = sorted(processes, key=lambda x: x['cpu_percent'] or 0, reverse=True)[:5]
        # Sort by memory usage
        top_mem = sorted(processes, key=lambda x: x['memory_percent'] or 0, reverse=True)[:5]
        
        return {
            'total': len(processes),
            'top_cpu': top_cpu,
            'top_memory': top_mem
        }
    
    def get_metrics(self):
        """Get all system metrics"""
        return {
            'timestamp': datetime.now().isoformat(),
            'system': self.get_system_info(),
            'cpu': self.get_cpu_info(),
            'memory': self.get_memory_info(),
            'disk': self.get_disk_info(),
            'network': self.get_network_info(),
            'processes': self.get_process_info()
        }
    
    def health_check(self):
        """Perform health check"""
        cpu_percent = psutil.cpu_percent(interval=1)
        mem_percent = psutil.virtual_memory().percent
        disk_percent = psutil.disk_usage('/').percent
        
        status = 'healthy'
        issues = []
        
        if cpu_percent > 90:
            status = 'warning'
            issues.append(f'High CPU usage: {cpu_percent}%')
        
        if mem_percent > 90:
            status = 'warning'
            issues.append(f'High memory usage: {mem_percent}%')
        
        if disk_percent > 90:
            status = 'critical'
            issues.append(f'High disk usage: {disk_percent}%')
        
        return {
            'status': status,
            'timestamp': datetime.now().isoformat(),
            'checks': {
                'cpu': {'value': cpu_percent, 'status': 'ok' if cpu_percent < 90 else 'warning'},
                'memory': {'value': mem_percent, 'status': 'ok' if mem_percent < 90 else 'warning'},
                'disk': {'value': disk_percent, 'status': 'ok' if disk_percent < 90 else 'critical'}
            },
            'issues': issues
        }
    
    def export_prometheus(self, data):
        """Export metrics in Prometheus format"""
        metrics = []
        
        # CPU metrics
        metrics.append(f'# HELP cpu_percent CPU usage percentage')
        metrics.append(f'# TYPE cpu_percent gauge')
        metrics.append(f'cpu_percent {data["cpu"]["percent"]}')
        
        # Memory metrics
        metrics.append(f'# HELP memory_percent Memory usage percentage')
        metrics.append(f'# TYPE memory_percent gauge')
        metrics.append(f'memory_percent {data["memory"]["virtual"]["percent"]}')
        
        metrics.append(f'# HELP memory_used_bytes Memory used in bytes')
        metrics.append(f'# TYPE memory_used_bytes gauge')
        metrics.append(f'memory_used_bytes {data["memory"]["virtual"]["used"]}')
        
        # Disk metrics
        for partition in data["disk"]["partitions"]:
            mountpoint = partition["mountpoint"].replace("/", "_").replace("\\", "_")
            metrics.append(f'# HELP disk_percent Disk usage percentage')
            metrics.append(f'# TYPE disk_percent gauge')
            metrics.append(f'disk_percent{{mountpoint="{partition["mountpoint"]}"}} {partition["percent"]}')
        
        # Network metrics
        if data["network"]["io"]:
            metrics.append(f'# HELP network_bytes_sent Network bytes sent')
            metrics.append(f'# TYPE network_bytes_sent counter')
            metrics.append(f'network_bytes_sent {data["network"]["io"]["bytes_sent"]}')
            
            metrics.append(f'# HELP network_bytes_recv Network bytes received')
            metrics.append(f'# TYPE network_bytes_recv counter')
            metrics.append(f'network_bytes_recv {data["network"]["io"]["bytes_recv"]}')
        
        # Process count
        metrics.append(f'# HELP process_count Total number of processes')
        metrics.append(f'# TYPE process_count gauge')
        metrics.append(f'process_count {data["processes"]["total"]}')
        
        return '\n'.join(metrics)


# Initialize monitor and Flask app
monitor = CloudNativeMonitor()
app = Flask(__name__)

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify(monitor.health_check())

@app.route('/metrics')
def metrics():
    """Prometheus metrics endpoint"""
    data = monitor.get_metrics()
    prometheus_format = monitor.export_prometheus(data)
    return Response(prometheus_format, mimetype='text/plain')

@app.route('/json')
def json_metrics():
    """JSON metrics endpoint"""
    return jsonify(monitor.get_metrics())

@app.route('/api/cpu')
def cpu_only():
    """Get only CPU metrics"""
    return jsonify(monitor.get_cpu_info())

@app.route('/api/memory')
def memory_only():
    """Get only memory metrics"""
    return jsonify(monitor.get_memory_info())

@app.route('/api/disk')
def disk_only():
    """Get only disk metrics"""
    return jsonify(monitor.get_disk_info())

@app.route('/api/network')
def network_only():
    """Get only network metrics"""
    return jsonify(monitor.get_network_info())

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 Cloud Native System Monitor API Starting...")
    print("=" * 60)
    print(f"❤️  Health Check:    http://localhost:5000/health")
    print(f"📈 Prometheus:       http://localhost:5000/metrics")
    print(f"📋 JSON (All):       http://localhost:5000/json")
    print(f"💻 CPU Only:         http://localhost:5000/api/cpu")
    print(f"💾 Memory Only:      http://localhost:5000/api/memory")
    print(f"💿 Disk Only:        http://localhost:5000/api/disk")
    print(f"🌐 Network Only:     http://localhost:5000/api/network")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5000, debug=True)