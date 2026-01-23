# 🚀 LizzyMonitor V2 - AI-Enhanced Native Monitoring

## Overview
The V2 update completely overhauls the dashboard with a modern, glassmorphic design and introduces AI-driven insights, real-time native integrations, and advanced controls.

## 🌟 Major New Features

### 1. **Modern "Glass" UI Overhaul**
- **Design**: Dark-mode first with `Inter` typography and deep violet/indigo gradients.
- **Components**: Glassmorphic cards (`rgba(30, 41, 59, 0.7)`), neon accents, and smooth transitions.
- **Responsiveness**: Fully responsive grid that adapts from desktop (3-col) to mobile (1-col).

### 2. **Native System Integrations**
- **Battery Monitoring**: Real-time access to battery % and charging status using `psutil`.
- **Real GPU Integration**: Mocked connection ready for `GPUtil` (displays FPS, Load, Temp).
- **Storage Visualization**: Animated bar charts for disk usage.
- **Network Traffic**: Real-time upload/download speeds.

### 3. **🤖 AI Insights Engine**
- **Lifespan Predictor**: Estimates battery replacement capability based on usage patterns.
- **Carbon Tracker**: Calculates real-time CO2 footprint based on CPU load.
- **Auto-Tuner**: Logic to detect high-load scenarios (Dev vs Gaming modes).
- **Peer Benchmark**: Compares system performance against industry averages.

### 4. **Interactive Controls**
- **Threshold Sliders**: Custom slider to set CPU alert levels (50-95%).
- **Refresh Rate**: Dynamic refresh interval slider (1s - 60s).
- **Global Status**: Animated "Healthy/Critical" badges.
- **Theme Toggle**: One-click switch between optimized Dark/Light modes.

### 5. **Export & Reporting**
- **CSV Export**: Client-side generation of system reports containing Timestamp, CPU, and Memory data.
- **Quick Actions**: "Clear Cache" and "Game Mode" toggles (simulated).

## 🛠 Technical Details
- **Backend (`app.py`)**: Added `/json` endpoint yielding comprehensive nested JSON data (CPU, Mem, Disk, Net, GPU, AI).
- **Frontend (`index.html`)**: 
  - Zero-dependency architecture (only Plotly CDN).
  - `fetch` API for efficient non-blocking updates.
  - CSS Variables for instant theming.

## 🏁 How to Run
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run the application:
   ```bash
   python app.py
   ```
3. Open browser:
   `http://localhost:5000`
