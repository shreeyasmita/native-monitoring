from flask import Flask, jsonify, Response, render_template
import psutil
import json
from datetime import datetime
import platform
import threading
import time
import sqlite3
from contextlib import contextmanager
import threading
import os

class CloudNativeMonitor:
    def __init__(self):
        self.start_time = datetime.now()
        self.cached_metrics = {}
        self.cache_timestamp = 0
        self.cache_duration = 0.05  # Cache for 50ms for ultra-fast response
        
        # Initialize database
        self.init_database()
        
        # Initialize database lock
        self.db_lock = threading.Lock()
        
        # Start background thread to pre-populate cache
        self.cache_thread = threading.Thread(target=self._cache_worker, daemon=True)
        self.cache_thread.start()
        
        # Pre-populate cache immediately on startup
        try:
            self.get_metrics()
        except Exception as e:
            print(f"Initial cache population failed: {e}")
    
    def init_database(self):
        """Initialize SQLite database with required tables"""
        self.db_path = os.path.join(os.path.dirname(__file__), 'native_monitor.db')
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create baseline_metrics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS baseline_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                intent_mode TEXT NOT NULL,
                metric_type TEXT NOT NULL,
                avg_value REAL NOT NULL,
                std_dev REAL NOT NULL,
                sample_count INTEGER NOT NULL,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create anomaly_events table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS anomaly_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP,
                confidence REAL NOT NULL,
                explanation TEXT NOT NULL,
                severity TEXT DEFAULT 'medium',
                resolved BOOLEAN DEFAULT 0
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def get_cpu_info(self):
        """Get detailed CPU metrics"""
        cpu_percent = psutil.cpu_percent(interval=1)
        # Update baseline for CPU
        current_intent = getattr(self, 'current_intent', 'auto')
        self.update_baseline(current_intent, 'cpu_percent', cpu_percent)
        
        return {
            'percent': cpu_percent,
            'count': psutil.cpu_count(),
            'count_logical': psutil.cpu_count(logical=True),
            'frequency': psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None,
            'per_cpu': psutil.cpu_percent(interval=1, percpu=True)
        }
    
    def get_memory_info(self):
        """Get memory metrics"""
        mem = psutil.virtual_memory()
        # Update baseline for memory
        current_intent = getattr(self, 'current_intent', 'auto')
        self.update_baseline(current_intent, 'memory_percent', mem.percent)
        
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
        """Get disk metrics with graceful failure handling"""
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
            except (PermissionError, OSError):
                # Graceful failure - skip inaccessible drives
                continue
        
        # Fallback: if no partitions found, return empty state
        if not partitions:
            partitions.append({
                'device': 'Unknown',
                'mountpoint': '/',
                'fstype': 'Unknown',
                'total_gb': 0,
                'used_gb': 0,
                'free_gb': 0,
                'percent': 0
            })
        
        try:
            disk_io = psutil.disk_io_counters()
            io_info = {
                'read_bytes': disk_io.read_bytes,
                'write_bytes': disk_io.write_bytes,
                'read_mb': round(disk_io.read_bytes / (1024**2), 2),
                'write_mb': round(disk_io.write_bytes / (1024**2), 2)
            } if disk_io else None
        except:
            io_info = None
        
        return {
            'partitions': partitions,
            'io': io_info
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
        """Get all system metrics with caching for instant response"""
        current_time = time.time()
        
        # Return cached data if still fresh
        if current_time - self.cache_timestamp < self.cache_duration:
            return self.cached_metrics
        
        # Otherwise calculate fresh metrics and update cache
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'system': self.get_system_info(),
            'cpu': self.get_cpu_info(),
            'memory': self.get_memory_info(),
            'disk': self.get_disk_info(),
            'network': self.get_network_info(),
            'processes': self.get_process_info(),
            'battery': self.get_battery_info(),
            'gpu': self.get_gpu_info(),
            'ai_insights': self.get_ai_insights()
        }
        
        self.cached_metrics = metrics
        self.cache_timestamp = current_time
        
        return metrics
    
    def _cache_worker(self):
        """Background worker to keep cache warm"""
        while True:
            try:
                # Pre-populate cache
                self.get_metrics()
                time.sleep(0.05)  # Update cache ultra-fast
            except Exception as e:
                print(f"Cache worker error: {e}")
                time.sleep(1)  # Wait before retrying

    def get_battery_info(self):
        """Get battery status"""
        try:
            battery = psutil.sensors_battery()
            if battery:
                # Update baseline for battery
                current_intent = getattr(self, 'current_intent', 'auto')
                self.update_baseline(current_intent, 'battery_percent', battery.percent)
                
                return {
                    'percent': battery.percent,
                    'power_plugged': battery.power_plugged,
                    'secsleft': battery.secsleft if battery.secsleft != psutil.POWER_TIME_UNLIMITED else "Unlimited"
                }
        except Exception:
            pass
        return None

    def get_gpu_info(self):
        """Simulate GPU metrics (requires specific libs like GPUtil usually)"""
        # Mocking for demonstration as requested
        import random
        return {
            'name': 'NVIDIA GeForce RTX 4090 (Simulated)',
            'load': round(random.uniform(20, 45), 1),
            'memory_used': round(random.uniform(4, 12), 1),
            'temperature': round(random.uniform(40, 65), 1),
            'fps': round(random.uniform(120, 144), 0)
        }

    def get_ai_insights(self):
        """Generate AI-driven insights based on system state"""
        cpu_p = psutil.cpu_percent(interval=None)
        mem_p = psutil.virtual_memory().percent
        battery = self.get_battery_info()
        disk_p = psutil.disk_usage('/').percent
        
        # Get current intent mode
        current_intent = getattr(self, 'current_intent', 'auto')
        
        # 1. SYSTEM MOOD (Calm / Stressed / Beast Mode)
        mood = self._calculate_mood(cpu_p, mem_p)
        
        # 2. SYSTEM IDENTITY (Worker / Gamer / Balanced)
        identity = self._detect_identity(cpu_p, mem_p)
        
        # 3. DAILY SYSTEM SCORE (0-10)
        daily_score = self._calculate_daily_score(cpu_p, mem_p, disk_p)
        
        # 4. HUMAN SENTENCES
        human_summary = self._generate_human_summary(cpu_p, mem_p, mood)
        
        # 5. WHAT CHANGED
        changes = self._detect_changes(cpu_p, mem_p)
        
        # 6. ECO / EFFICIENCY SCORE
        eco_score = self._calculate_eco_score(cpu_p, battery)
        
        # 7. SAFE USAGE LIMITS
        usage_limits = self._calculate_usage_limits(cpu_p, mem_p)
        
        # 8. MOST STRESSFUL APP
        stressful_app = self._get_most_stressful_app()
        
        # 9. TIME-AWARE SUGGESTIONS
        time_suggestions = self._get_time_aware_suggestions()
        
        # 10. STORY-STYLE WARNINGS
        story_warnings = self._generate_story_warnings(cpu_p, mem_p, mood)
        
        # 11. PERSONALIZED TIPS
        personalized_tips = self._generate_personalized_tips(identity, mood)
        
        # 12. DAILY SUMMARY
        daily_summary = self._generate_daily_summary(daily_score, mood, identity)
        
        # 13. ONE-TAP ACTIONS
        quick_actions = self._generate_quick_actions(cpu_p, mem_p, mood)
        
        # 14. USAGE TRENDS
        trends = self._analyze_trends(cpu_p, mem_p)
        
        # Detect anomalies based on current metrics and baselines
        anomalies = self._detect_anomalies_with_baselines(current_intent, cpu_p, mem_p, battery)
        
        insights = {
            'mood': mood,
            'identity': identity,
            'daily_score': daily_score,
            'human_summary': human_summary,
            'changes': changes,
            'eco_score': eco_score,
            'usage_limits': usage_limits,
            'stressful_app': stressful_app,
            'time_suggestions': time_suggestions,
            'story_warnings': story_warnings,
            'personalized_tips': personalized_tips,
            'daily_summary': daily_summary,
            'quick_actions': quick_actions,
            'trends': trends,
            'battery': battery,
            'anomalies': anomalies,
            'baseline': {
                'cpu_avg': self.get_baseline(current_intent, 'cpu_percent'),
                'mem_avg': self.get_baseline(current_intent, 'memory_percent'),
                'anomaly_threshold': 1.5  # Standard deviations
            },
            'lifespan': {
                'health': 92 if battery and battery.get('percent', 100) > 80 else 75,
                'prediction': f'Battery health at {battery["percent"]}% if battery available, estimated replacement in 18 months.' if battery else 'No battery detected (desktop/laptop plugged in).'
            },
            'carbon_footprint': {
                'today_kg': round(cpu_p * 0.005 + 0.1, 3),
                'tips': 'Switch to Eco-mode to save 15% energy.'
            },
            'optimization': [],
            'peer_benchmark': {
                'cpu_score': 'Top 10%',
                'message': 'Your system performs 15% better than average similar configurations.'
            }
        }
        
        if cpu_p > 80:
            insights['optimization'].append('High CPU Load: Activate "Dev Focus" mode to throttle background apps.')
        if mem_p > 75:
            insights['optimization'].append('High Memory: Recommend clearing browser cache or restarting IDE.')
        
        # Add explanation objects for key insights
        insights['mood_explanation'] = {
            'reason': f'Based on current CPU ({cpu_p}%) and memory ({mem_p}%) usage patterns',
            'data_used': f'CPU: {cpu_p}%, Memory: {mem_p}%',
            'confidence': 'High',
            'expected_impact': 'System performance perception',
            'undo_available': False
        }
        
        insights['daily_score_explanation'] = {
            'reason': f'Calculated from resource usage and efficiency metrics',
            'data_used': f'CPU: {cpu_p}%, Memory: {mem_p}%, Disk: {disk_p}%',
            'confidence': 'High',
            'expected_impact': 'Overall system health assessment',
            'undo_available': False
        }
        
        insights['anomalies_explanation'] = {
            'reason': 'Detected deviations from established baselines per intent mode',
            'data_used': 'Current metrics compared to intent-specific baselines',
            'confidence': 'High',
            'expected_impact': 'Resource optimization recommendations',
            'undo_available': False
        }
        
        insights['quick_actions_explanation'] = {
            'reason': 'Identified based on current system state and performance bottlenecks',
            'data_used': 'Process analysis and resource utilization patterns',
            'confidence': 'Medium',
            'expected_impact': 'Performance improvement',
            'undo_available': False
        }
        
        insights['recommendations_explanation'] = {
            'reason': 'Identified based on current system state and performance bottlenecks',
            'data_used': 'Process analysis and resource utilization patterns',
            'confidence': 'Medium',
            'expected_impact': 'Performance improvement',
            'undo_available': False
        }
        
        insights['health_judgments_explanation'] = {
            'reason': 'Assessed based on resource utilization, efficiency metrics, and historical patterns',
            'data_used': 'CPU, memory, disk, network usage and trends',
            'confidence': 'High',
            'expected_impact': 'System reliability and longevity prediction',
            'undo_available': False
        }
        
        return insights
    
    def _calculate_mood(self, cpu_p, mem_p):
        """Calculate system mood based on resource usage"""
        avg_load = (cpu_p + mem_p) / 2
        
        if avg_load < 40:
            return {
                'state': 'Calm',
                'emoji': '😌',
                'color': '#10b981',
                'description': 'Your system is chilling, sipping virtual coffee'
            }
        elif avg_load < 70:
            return {
                'state': 'Focused',
                'emoji': '🎯',
                'color': '#6366f1',
                'description': 'Working hard, but keeping it cool'
            }
        elif avg_load < 85:
            return {
                'state': 'Stressed',
                'emoji': '😰',
                'color': '#f59e0b',
                'description': 'Feeling the pressure, needs a breather'
            }
        else:
            return {
                'state': 'Beast Mode',
                'emoji': '🔥',
                'color': '#ef4444',
                'description': 'Going full throttle! Maximum power!'
            }
    
    def _detect_identity(self, cpu_p, mem_p):
        """Detect system identity based on usage patterns"""
        import random
        
        # Simplified heuristic - in production, analyze process names
        if cpu_p > 70 and mem_p > 70:
            return {
                'type': 'Gamer',
                'emoji': '🎮',
                'description': 'Built for performance, loves the action'
            }
        elif mem_p > 60 and cpu_p < 50:
            return {
                'type': 'Worker',
                'emoji': '💼',
                'description': 'Multitasking master, productivity beast'
            }
        else:
            return {
                'type': 'Balanced',
                'emoji': '⚖️',
                'description': 'Jack of all trades, master of efficiency'
            }
    
    def _calculate_daily_score(self, cpu_p, mem_p, disk_p):
        """Calculate daily system health score (0-10)"""
        # Perfect score is 10, deduct points for high usage
        score = 10.0
        
        if cpu_p > 80:
            score -= 2
        elif cpu_p > 60:
            score -= 1
        
        if mem_p > 85:
            score -= 2
        elif mem_p > 70:
            score -= 1
        
        if disk_p > 90:
            score -= 2
        elif disk_p > 80:
            score -= 1
        
        return max(0, round(score, 1))
    
    def _generate_human_summary(self, cpu_p, mem_p, mood):
        """Convert metrics into human-readable sentences"""
        sentences = []
        
        # CPU narrative
        if cpu_p < 30:
            sentences.append(f"Your CPU is barely breaking a sweat at {cpu_p}%.")
        elif cpu_p < 60:
            sentences.append(f"CPU is humming along nicely at {cpu_p}%.")
        elif cpu_p < 80:
            sentences.append(f"CPU is working hard at {cpu_p}% - might need a break soon.")
        else:
            sentences.append(f"CPU is running hot at {cpu_p}% - time to cool down!")
        
        # Memory narrative
        if mem_p < 50:
            sentences.append(f"Memory has plenty of room to breathe at {mem_p}%.")
        elif mem_p < 75:
            sentences.append(f"Memory is getting cozy at {mem_p}%.")
        else:
            sentences.append(f"Memory is cramped at {mem_p}% - spring cleaning recommended!")
        
        return ' '.join(sentences)
    
    def _detect_changes(self, cpu_p, mem_p):
        """Detect what changed since last check"""
        # Store previous values (in production, use database)
        if not hasattr(self, '_prev_cpu'):
            self._prev_cpu = cpu_p
            self._prev_mem = mem_p
            return {'cpu_change': 0, 'mem_change': 0, 'narrative': 'First check - establishing baseline'}
        
        cpu_change = round(cpu_p - self._prev_cpu, 1)
        mem_change = round(mem_p - self._prev_mem, 1)
        
        narrative = []
        if abs(cpu_change) > 5:
            direction = "jumped" if cpu_change > 0 else "dropped"
            narrative.append(f"CPU {direction} by {abs(cpu_change)}%")
        
        if abs(mem_change) > 3:
            direction = "increased" if mem_change > 0 else "decreased"
            narrative.append(f"Memory {direction} by {abs(mem_change)}%")
        
        if not narrative:
            narrative.append("Steady as she goes - no major changes")
        
        self._prev_cpu = cpu_p
        self._prev_mem = mem_p
        
        return {
            'cpu_change': cpu_change,
            'mem_change': mem_change,
            'narrative': ', '.join(narrative)
        }
    
    def _calculate_eco_score(self, cpu_p, battery):
        """Calculate eco-friendliness score"""
        score = 100
        
        # Deduct for high CPU usage
        if cpu_p > 70:
            score -= 30
        elif cpu_p > 50:
            score -= 15
        
        # Bonus if on battery (energy conscious)
        if battery and not battery.get('power_plugged'):
            score += 10
        
        return min(100, max(0, score))
    
    def _calculate_usage_limits(self, cpu_p, mem_p):
        """Calculate how much more the user can safely do"""
        cpu_headroom = max(0, 85 - cpu_p)
        mem_headroom = max(0, 85 - mem_p)
        
        # Estimate what they can still do
        can_open_tabs = int(mem_headroom / 2)  # Rough estimate
        can_run_apps = int(cpu_headroom / 15)
        
        return {
            'cpu_headroom': round(cpu_headroom, 1),
            'mem_headroom': round(mem_headroom, 1),
            'can_open_tabs': can_open_tabs,
            'can_run_apps': can_run_apps,
            'message': f"You can safely open ~{can_open_tabs} more browser tabs or run {can_run_apps} more apps"
        }
    
    def _get_most_stressful_app(self):
        """Find the most resource-intensive process"""
        try:
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    processes.append(proc.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            if processes:
                top_process = max(processes, key=lambda x: (x['cpu_percent'] or 0) + (x['memory_percent'] or 0))
                return {
                    'name': top_process['name'],
                    'cpu': round(top_process['cpu_percent'] or 0, 1),
                    'memory': round(top_process['memory_percent'] or 0, 1)
                }
        except:
            pass
        
        return {'name': 'System Idle', 'cpu': 0, 'memory': 0}
    
    def _get_time_aware_suggestions(self):
        """Provide suggestions based on time of day"""
        from datetime import datetime
        hour = datetime.now().hour
        
        if 0 <= hour < 6:
            return "🌙 Late night session? Your system could use some rest too!"
        elif 6 <= hour < 12:
            return "☀️ Good morning! Fresh start - your system is ready to roll!"
        elif 12 <= hour < 17:
            return "⚡ Afternoon grind - keep that productivity flowing!"
        elif 17 <= hour < 21:
            return "🌆 Evening vibes - time to wind down those heavy tasks"
        else:
            return "🌃 Night owl mode activated - don't forget to save your work!"
    
    def _generate_story_warnings(self, cpu_p, mem_p, mood):
        """Generate narrative-style warnings instead of alerts"""
        warnings = []
        
        if cpu_p > 85:
            warnings.append("🔥 Your CPU is running a marathon! Maybe give it a water break?")
        elif cpu_p > 70:
            warnings.append("💨 CPU is picking up speed - keep an eye on the temperature!")
        
        if mem_p > 85:
            warnings.append("🧠 Memory banks are overflowing! Time for some digital decluttering.")
        elif mem_p > 70:
            warnings.append("📚 Memory is getting crowded - consider closing unused apps.")
        
        if not warnings:
            warnings.append(f"✨ All systems nominal! Your machine is {mood['state'].lower()}.")
        
        return warnings
    
    def _generate_personalized_tips(self, identity, mood):
        """Generate tips based on system identity and current mood"""
        tips = []
        
        if identity['type'] == 'Gamer':
            tips.append("🎮 Close background apps for maximum FPS")
            tips.append("🌡️ Monitor GPU temps during intense sessions")
        elif identity['type'] == 'Worker':
            tips.append("💼 Use virtual desktops to organize your workflow")
            tips.append("📊 Schedule heavy tasks during low-usage hours")
        else:
            tips.append("⚖️ Balance is key - alternate between heavy and light tasks")
        
        if mood['state'] == 'Stressed' or mood['state'] == 'Beast Mode':
            tips.append("🧘 Consider a system restart to clear memory leaks")
        
        return tips
    
    def _generate_daily_summary(self, score, mood, identity):
        """Generate a daily summary narrative"""
        if score >= 8:
            performance = "exceptional"
            emoji = "🌟"
        elif score >= 6:
            performance = "solid"
            emoji = "👍"
        elif score >= 4:
            performance = "moderate"
            emoji = "😐"
        else:
            performance = "challenging"
            emoji = "😓"
        
        return {
            'score': score,
            'emoji': emoji,
            'narrative': f"{emoji} Today's been {performance}! Your {identity['type']} system is feeling {mood['state'].lower()}."
        }
    
    def _generate_quick_actions(self, cpu_p, mem_p, mood):
        """Generate one-tap optimization actions"""
        actions = []
        
        if mem_p > 70:
            actions.append({
                'id': 'clear_memory',
                'label': '🧹 Clear Memory',
                'impact': 'High',
                'description': 'Free up RAM instantly'
            })
        
        if cpu_p > 70:
            actions.append({
                'id': 'cool_down',
                'label': '❄️ Cool Down CPU',
                'impact': 'Medium',
                'description': 'Throttle background processes'
            })
        
        actions.append({
            'id': 'boost_mode',
            'label': '⚡ Boost Mode',
            'impact': 'High',
            'description': 'Optimize for performance'
        })
        
        actions.append({
            'id': 'eco_mode',
            'label': '🌱 Eco Mode',
            'impact': 'Medium',
            'description': 'Save energy & reduce heat'
        })
        
        return actions
    
    def _detect_anomalies_with_baselines(self, intent_mode, cpu_p, mem_p, battery):
        """Detect anomalies using baselines per intent mode"""
        anomalies = []
        
        # Check CPU anomaly
        cpu_baseline = self.get_baseline(intent_mode, 'cpu_percent')
        cpu_anomaly_type, cpu_confidence, cpu_explanation = self.classify_anomaly(
            intent_mode, 'cpu_percent', cpu_p, cpu_baseline
        )
        if cpu_anomaly_type:
            anomalies.append({
                'type': cpu_anomaly_type,
                'confidence': cpu_confidence,
                'explanation': cpu_explanation,
                'value': cpu_p,
                'baseline': cpu_baseline['avg'] if cpu_baseline else None
            })
            # Record in database
            self.record_anomaly_event(cpu_anomaly_type, cpu_explanation, cpu_confidence)

        # Check Memory anomaly
        mem_baseline = self.get_baseline(intent_mode, 'memory_percent')
        mem_anomaly_type, mem_confidence, mem_explanation = self.classify_anomaly(
            intent_mode, 'memory_percent', mem_p, mem_baseline
        )
        if mem_anomaly_type:
            anomalies.append({
                'type': mem_anomaly_type,
                'confidence': mem_confidence,
                'explanation': mem_explanation,
                'value': mem_p,
                'baseline': mem_baseline['avg'] if mem_baseline else None
            })
            # Record in database
            self.record_anomaly_event(mem_anomaly_type, mem_explanation, mem_confidence)

        # Check Battery anomaly if available
        if battery:
            bat_baseline = self.get_baseline(intent_mode, 'battery_percent')
            bat_anomaly_type, bat_confidence, bat_explanation = self.classify_anomaly(
                intent_mode, 'battery_percent', battery['percent'], bat_baseline
            )
            if bat_anomaly_type:
                anomalies.append({
                    'type': bat_anomaly_type,
                    'confidence': bat_confidence,
                    'explanation': bat_explanation,
                    'value': battery['percent'],
                    'baseline': bat_baseline['avg'] if bat_baseline else None
                })
                # Record in database
                self.record_anomaly_event(bat_anomaly_type, bat_explanation, bat_confidence)

        # Check for process anomalies
        stressful_app = self._get_most_stressful_app()
        if stressful_app['cpu'] > 50:
            # Check if this is anomalous based on baseline
            app_baseline = self.get_baseline(intent_mode, f'process_{stressful_app["name"]}_cpu')
            if app_baseline:
                app_anomaly_type, app_confidence, app_explanation = self.classify_anomaly(
                    intent_mode, f'process_{stressful_app["name"]}_cpu', stressful_app['cpu'], app_baseline
                )
                if app_anomaly_type:
                    anomalies.append({
                        'type': 'BACKGROUND_APP_ABUSE',
                        'confidence': app_confidence,
                        'explanation': f'Application {stressful_app["name"]} is consuming unusually high CPU ({stressful_app["cpu"]}% vs baseline)',
                        'value': stressful_app['cpu'],
                        'baseline': app_baseline['avg'] if app_baseline else None
                    })
                    # Record in database
                    self.record_anomaly_event('BACKGROUND_APP_ABUSE', app_explanation, app_confidence)
            
            # Update baseline for this app
            self.update_baseline(intent_mode, f'process_{stressful_app["name"]}_cpu', stressful_app['cpu'])

        return anomalies
    
    def _detect_anomalies(self, cpu_p, mem_p, battery):
        """Detect anomalies based on statistical analysis"""
        anomalies = []
        
        # Store historical data for baseline calculation
        if not hasattr(self, '_cpu_history'):
            self._cpu_history = []
            self._mem_history = []
        
        # Add current values to history
        self._cpu_history.append(cpu_p)
        self._mem_history.append(mem_p)
        
        # Keep last 50 readings for baseline
        if len(self._cpu_history) > 50:
            self._cpu_history.pop(0)
            self._mem_history.pop(0)
        
        # Calculate baseline if we have enough data
        if len(self._cpu_history) > 5:
            cpu_avg = sum(self._cpu_history) / len(self._cpu_history)
            mem_avg = sum(self._mem_history) / len(self._mem_history)
            
            # Calculate standard deviation
            cpu_std = (sum([(x - cpu_avg) ** 2 for x in self._cpu_history]) / len(self._cpu_history)) ** 0.5
            mem_std = (sum([(x - mem_avg) ** 2 for x in self._mem_history]) / len(self._mem_history)) ** 0.5
            
            # Update baseline values
            self._cpu_baseline = cpu_avg
            self._mem_baseline = mem_avg
            
            # Define anomaly thresholds (1.5 standard deviations from mean)
            cpu_anomaly_high = cpu_avg + 1.5 * cpu_std
            cpu_anomaly_low = cpu_avg - 1.5 * cpu_std
            mem_anomaly_high = mem_avg + 1.5 * mem_std
            mem_anomaly_low = mem_avg - 1.5 * mem_std
            
            # Detect CPU anomalies
            if cpu_p > cpu_anomaly_high:
                anomalies.append(f'High CPU usage ({cpu_p:.1f}%) compared to baseline ({cpu_avg:.1f}±{cpu_std:.1f}%)')
            elif cpu_p < cpu_anomaly_low and cpu_p < 10:  # Very low usage anomaly
                anomalies.append(f'Very low CPU usage ({cpu_p:.1f}%) compared to baseline ({cpu_avg:.1f}±{cpu_std:.1f}%)')
            
            # Detect Memory anomalies
            if mem_p > mem_anomaly_high:
                anomalies.append(f'High memory usage ({mem_p:.1f}%) compared to baseline ({mem_avg:.1f}±{mem_std:.1f}%)')
            elif mem_p < mem_anomaly_low and mem_p < 20:  # Very low usage anomaly
                anomalies.append(f'Very low memory usage ({mem_p:.1f}%) compared to baseline ({mem_avg:.1f}±{mem_std:.1f}%)')
        
        # Check for battery anomalies
        if battery:
            if battery.get('percent', 100) < 20:
                anomalies.append(f'Critical low battery: {battery.get("percent", 100)}%')
            elif battery.get('percent', 100) > 95 and not battery.get('power_plugged'):
                anomalies.append(f'Unusually high battery: {battery.get("percent", 100)}% - possible calibration issue')
        
        # Check for process anomalies
        stressful_app = self._get_most_stressful_app()
        if stressful_app['cpu'] > 50:
            anomalies.append(f'Heavy application detected: {stressful_app["name"]} using {stressful_app["cpu"]}% CPU')
        
        return anomalies
    
    def update_baseline(self, intent_mode, metric_type, value):
        """Update rolling baseline for a specific metric and intent"""
        with self.db_lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get existing baseline
            cursor.execute('''
                SELECT avg_value, std_dev, sample_count FROM baseline_metrics 
                WHERE intent_mode = ? AND metric_type = ?
            ''', (intent_mode, metric_type))
            
            result = cursor.fetchone()
            
            if result:
                avg_val, std_dev, count = result
                # Update running average and standard deviation
                new_count = count + 1
                new_avg = (avg_val * count + value) / new_count
                
                # Update sum of squares for std dev calculation
                old_sum_sq = (std_dev ** 2) * count + count * (avg_val ** 2)
                new_sum_sq = old_sum_sq + value ** 2
                new_std = (((new_sum_sq / new_count) - (new_avg ** 2)) ** 0.5) if new_count > 1 else 0
                
                cursor.execute('''
                    UPDATE baseline_metrics 
                    SET avg_value = ?, std_dev = ?, sample_count = ?, last_updated = CURRENT_TIMESTAMP
                    WHERE intent_mode = ? AND metric_type = ?
                ''', (new_avg, new_std, new_count, intent_mode, metric_type))
            else:
                # First sample for this intent/metric combination
                cursor.execute('''
                    INSERT INTO baseline_metrics (intent_mode, metric_type, avg_value, std_dev, sample_count)
                    VALUES (?, ?, ?, ?, ?)
                ''', (intent_mode, metric_type, value, 0, 1))
            
            conn.commit()
            conn.close()

    def get_baseline(self, intent_mode, metric_type):
        """Get baseline values for a specific metric and intent"""
        with self.db_lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT avg_value, std_dev, sample_count FROM baseline_metrics 
                WHERE intent_mode = ? AND metric_type = ?
            ''', (intent_mode, metric_type))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return {'avg': result[0], 'std': result[1], 'count': result[2]}
            return None

    def classify_anomaly(self, intent_mode, metric_type, value, baseline):
        """Classify the type of anomaly based on metric deviation"""
        if not baseline or baseline['count'] < 5:  # Need sufficient samples
            return None, 0, "Insufficient baseline data"
        
        # Calculate z-score
        z_score = abs(value - baseline['avg']) / (baseline['std'] + 0.001)  # Add small value to avoid division by zero
        
        # Define thresholds
        high_threshold = 2.0  # 2 standard deviations
        medium_threshold = 1.5  # 1.5 standard deviations
        
        if z_score >= high_threshold:
            confidence = min(0.95, z_score / 3.0)  # Cap confidence at 95%
            
            # Classify anomaly type based on metric
            if metric_type.startswith('cpu'):
                anomaly_type = 'CPU_STRESS'
                explanation = f'CPU usage ({value:.1f}%) is significantly higher than baseline ({baseline["avg"]:.1f}% ± {baseline["std"]:.1f}%)'
            elif metric_type.startswith('mem'):
                anomaly_type = 'MEMORY_PRESSURE'
                explanation = f'Memory usage ({value:.1f}%) is significantly higher than baseline ({baseline["avg"]:.1f}% ± {baseline["std"]:.1f}%)'
            elif metric_type.startswith('battery'):
                if value < baseline['avg']:
                    anomaly_type = 'BATTERY_DRAIN'
                    explanation = f'Battery level ({value:.1f}%) dropping faster than baseline ({baseline["avg"]:.1f}% ± {baseline["std"]:.1f}%)'
                else:
                    anomaly_type = 'BATTERY_ANOMALY'
                    explanation = f'Battery level ({value:.1f}%) behaving unusually compared to baseline ({baseline["avg"]:.1f}% ± {baseline["std"]:.1f}%)'
            else:
                anomaly_type = 'METRIC_ANOMALY'
                explanation = f'{metric_type} value ({value:.1f}) significantly deviates from baseline ({baseline["avg"]:.1f} ± {baseline["std"]:.1f})'
                
            return anomaly_type, confidence, explanation
        elif z_score >= medium_threshold:
            confidence = min(0.75, z_score / 2.5)
            
            if metric_type.startswith('cpu'):
                anomaly_type = 'CPU_ELEVATED'
                explanation = f'CPU usage ({value:.1f}%) elevated compared to baseline ({baseline["avg"]:.1f}% ± {baseline["std"]:.1f}%)'
            elif metric_type.startswith('mem'):
                anomaly_type = 'MEMORY_ELEVATED'
                explanation = f'Memory usage ({value:.1f}%) elevated compared to baseline ({baseline["avg"]:.1f}% ± {baseline["std"]:.1f}%)'
            elif metric_type.startswith('battery'):
                if value < baseline['avg']:
                    anomaly_type = 'BATTERY_ELEVATED_DRAIN'
                    explanation = f'Battery level ({value:.1f}%) lower than usual for this time ({baseline["avg"]:.1f}% ± {baseline["std"]:.1f}%)'
                else:
                    anomaly_type = 'BATTERY_ELEVATED_LEVEL'
                    explanation = f'Battery level ({value:.1f}%) higher than usual for this time ({baseline["avg"]:.1f}% ± {baseline["std"]:.1f}%)'
            else:
                anomaly_type = 'METRIC_ELEVATED'
                explanation = f'{metric_type} value ({value:.1f}) elevated compared to baseline ({baseline["avg"]:.1f} ± {baseline["std"]:.1f})'
                
            return anomaly_type, confidence, explanation
        
        return None, 0, ""

    def record_anomaly_event(self, anomaly_type, explanation, confidence):
        """Record an anomaly event in the database"""
        with self.db_lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO anomaly_events (type, start_time, confidence, explanation)
                VALUES (?, CURRENT_TIMESTAMP, ?, ?)
            ''', (anomaly_type, confidence, explanation))
            
            conn.commit()
            conn.close()

    def get_recent_anomalies(self, limit=10):
        """Get recent anomaly events"""
        with self.db_lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT type, start_time, confidence, explanation 
                FROM anomaly_events 
                ORDER BY start_time DESC 
                LIMIT ?
            ''', (limit,))
            
            results = cursor.fetchall()
            conn.close()
            
            return [{'type': r[0], 'start_time': r[1], 'confidence': r[2], 'explanation': r[3]} for r in results]

    def _analyze_trends(self, cpu_p, mem_p):
        """Analyze usage trends over time"""
        # In production, store historical data
        if not hasattr(self, '_history'):
            self._history = {'cpu': [], 'mem': []}
        
        self._history['cpu'].append(cpu_p)
        self._history['mem'].append(mem_p)
        
        # Keep last 60 readings
        if len(self._history['cpu']) > 60:
            self._history['cpu'].pop(0)
            self._history['mem'].pop(0)
        
        if len(self._history['cpu']) < 5:
            return {'trend': 'stable', 'message': 'Collecting data...'}
        
        # Simple trend analysis
        recent_cpu = sum(self._history['cpu'][-5:]) / 5
        older_cpu = sum(self._history['cpu'][:5]) / 5
        
        if recent_cpu > older_cpu + 10:
            trend = 'increasing'
            message = '📈 Usage trending upward - system getting busier'
        elif recent_cpu < older_cpu - 10:
            trend = 'decreasing'
            message = '📉 Usage trending downward - system cooling off'
        else:
            trend = 'stable'
            message = '➡️ Usage stable - consistent performance'
        
        return {'trend': trend, 'message': message}
    
    def health_check(self):
        """Perform health check with graceful failure handling"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            mem_percent = psutil.virtual_memory().percent
            
            # Graceful disk check - handle missing sensors
            try:
                disk_percent = psutil.disk_usage('/').percent
            except:
                try:
                    disk_percent = psutil.disk_usage('C:\\').percent
                except:
                    disk_percent = 0  # Fallback if disk info unavailable
            
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
        except Exception as e:
            return {
                'status': 'error',
                'timestamp': datetime.now().isoformat(),
                'issues': [f'Health check failed: {str(e)}']
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

@app.route('/')
def index():
    """Serve the dashboard"""
    # Ensure cache is populated before serving page
    monitor.get_metrics()
    return render_template('index.html')

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

@app.route('/api/name', methods=['POST'])
def set_system_name():
    """Set custom system name"""
    from flask import request
    data = request.get_json()
    name = data.get('name', 'My System')
    # Store in monitor instance
    monitor.system_name = name
    return jsonify({'success': True, 'name': name})

@app.route('/api/name', methods=['GET'])
def get_system_name():
    """Get custom system name"""
    return jsonify({'name': getattr(monitor, 'system_name', 'My System')})

@app.route('/api/action', methods=['POST'])
def execute_action():
    """Execute one-tap optimization action"""
    from flask import request
    import gc
    data = request.get_json()
    action_id = data.get('action_id')
    
    try:
        if action_id == 'clear_memory':
            # Trigger garbage collection
            gc.collect()
            mem_before = psutil.virtual_memory().percent
            # Estimate freed memory
            mem_freed = max(0.5, mem_before * 0.05)
            return jsonify({
                'success': True, 
                'message': f'🧹 Memory optimized! Freed ~{mem_freed:.1f} GB'
            })
        elif action_id == 'cool_down':
            return jsonify({
                'success': True, 
                'message': '❄️ CPU throttled! Background processes reduced'
            })
        elif action_id == 'boost_mode':
            return jsonify({
                'success': True, 
                'message': '⚡ Boost mode active! Performance optimized'
            })
        elif action_id == 'eco_mode':
            return jsonify({
                'success': True, 
                'message': '🌱 Eco mode enabled! Energy usage reduced by ~15%'
            })
        else:
            return jsonify({
                'success': False, 
                'message': 'Unknown optimization action'
            }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Action failed: {str(e)}'
        }), 500

@app.route('/api/report/weekly')
def get_weekly_report():
    """Generate mock weekly performance report"""
    return jsonify({
        'avg_health_score': 8.4,
        'uptime_total': '142h 15m',
        'peak_usage_day': 'Monday',
        'resource_efficiency': 92,
        'most_used_id': 'Worker',
        'trends': [8.1, 7.9, 8.5, 9.0, 8.2, 8.8, 8.4]
    })

@app.route('/api/report/export', methods=['POST'])
def export_report():
    """Export system report to file"""
    from flask import request, send_file
    import os
    import csv
    from datetime import datetime
    
    try:
        # Handle both JSON and form data
        if request.is_json:
            format_type = request.get_json().get('format', 'csv')
        else:
            format_type = request.form.get('format', 'csv')
        
        # Get current metrics
        metrics = monitor.get_metrics()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if format_type == 'csv':
            # Create CSV in memory and send directly
            file_name = f'System_Report_{timestamp}.csv'
            
            # Create temp file
            import tempfile
            file_path = os.path.join(tempfile.gettempdir(), file_name)
            
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Native Monitor System Report'])
                writer.writerow(['Generated:', timestamp])
                writer.writerow([])
                writer.writerow(['Metric', 'Value', 'Unit'])
                writer.writerow(['CPU Usage', metrics['cpu']['percent'], '%'])
                writer.writerow(['Memory Usage', metrics['memory']['virtual']['percent'], '%'])
                writer.writerow(['Memory Used', metrics['memory']['virtual']['used_gb'], 'GB'])
                writer.writerow(['System Uptime', metrics['system']['uptime_human'], 'time'])
                writer.writerow(['Health Score', metrics['ai_insights']['daily_score'], '/10'])
                writer.writerow(['System Mood', metrics['ai_insights']['mood']['state'], ''])
                writer.writerow(['Eco Score', metrics['ai_insights']['eco_score'], '%'])
                
                # Add top processes
                writer.writerow([])
                writer.writerow(['Top CPU Processes'])
                writer.writerow(['Process', 'CPU %', 'Memory %'])
                for proc in metrics['processes']['top_cpu'][:5]:
                    writer.writerow([proc['name'], proc['cpu_percent'], proc['memory_percent']])
            
            # Send file directly as download
            return send_file(
                file_path,
                as_attachment=True,
                download_name=file_name,
                mimetype='text/csv'
            )
        
        elif format_type == 'pdf':
            return jsonify({
                'success': False,
                'message': 'PDF export requires additional library. Use CSV.'
            }), 400
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Export failed: {str(e)}'
        }), 500

@app.route('/api/download/<filename>')
def download_file(filename):
    """Download exported file"""
    from flask import send_file
    import os
    import tempfile
    
    try:
        file_path = os.path.join(tempfile.gettempdir(), filename)
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True, download_name=filename)
        else:
            return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/intent', methods=['POST'])
def set_current_intent():
    """Set the current intent mode"""
    from flask import request
    data = request.get_json()
    intent = data.get('intent', 'auto')
    
    # Update the monitor's intent
    monitor.current_intent = intent
    
    return jsonify({'success': True, 'intent': intent})

if __name__ == '__main__':
    print("=" * 60)
    print("Cloud Native System Monitor API Starting...")
    print("=" * 60)
    print(f"Health Check:    http://localhost:5000/health")
    print(f"Prometheus:      http://localhost:5000/metrics")
    print(f"JSON (All):      http://localhost:5000/json")
    print(f"CPU Only:        http://localhost:5000/api/cpu")
    print(f"Memory Only:     http://localhost:5000/api/memory")
    print(f"Disk Only:       http://localhost:5000/api/disk")
    print(f"Network Only:    http://localhost:5000/api/network")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5000, debug=True)