# 🎨 LizzyMonitor Theme System

## Available Themes

### 1. 🌙 **Dark Theme** (Default)
- **Primary Color:** #667eea (Purple)
- **Secondary Color:** #764ba2 (Deep Purple)
- **Background:** Dark Navy (#0f0f23 → #1a1a3e → #16213e)
- **Text:** Light Silver (#e0e0e0)
- **Use Case:** Professional, low-light environments, reduces eye strain
- **Best For:** 24/7 monitoring, night shifts

### 2. ☀️ **Light Theme**
- **Primary Color:** #667eea (Purple)
- **Secondary Color:** #764ba2 (Deep Purple)
- **Background:** Light Gray/White (#f5f7fa → #ffffff)
- **Text:** Dark Gray (#2c3e50)
- **Use Case:** Daytime use, office environments, accessibility
- **Best For:** Print-friendly, presentations

### 3. 🌊 **Ocean Theme**
- **Primary Color:** #00a8e8 (Cyan Blue)
- **Secondary Color:** #005f8f (Deep Blue)
- **Background:** Ocean Dark (#0a1f2e → #16324f → #1f4d6b)
- **Text:** Sky Blue (#d4e8f7)
- **Use Case:** Calming, technology-focused, professional
- **Best For:** Extended monitoring sessions, water utilities

### 4. 🌲 **Forest Theme**
- **Primary Color:** #2ecc71 (Green)
- **Secondary Color:** #27ae60 (Dark Green)
- **Background:** Forest Dark (#0d2818 → #1a4d2e → #2d5a3d)
- **Text:** Light Green (#d1e8d4)
- **Use Case:** Natural, environmental, eco-friendly
- **Best For:** Green computing initiatives, nature-themed organizations

### 5. 🌅 **Sunset Theme**
- **Primary Color:** #ff6b35 (Orange Red)
- **Secondary Color:** #e63946 (Crimson)
- **Background:** Warm Dark (#2c1810 → #4a2c1f → #6b3f2e)
- **Text:** Warm Beige (#f1d5c4)
- **Use Case:** Warm, creative, attention-grabbing
- **Best For:** Marketing teams, creative agencies

### 6. ⚡ **Cyber Theme**
- **Primary Color:** #00ff00 (Neon Green)
- **Secondary Color:** #00cc00 (Bright Green)
- **Background:** Matrix Dark (#0a0e27 → #1a1f3a → #2a2f4a)
- **Text:** Cyber Green (#ccffcc)
- **Use Case:** Futuristic, high-tech, hacker aesthetic
- **Best For:** DevOps teams, cybersecurity professionals

### 7. 🌸 **Sakura Theme**
- **Primary Color:** #ff69b4 (Hot Pink)
- **Secondary Color:** #ff1493 (Deep Pink)
- **Background:** Cherry Dark (#2a1a25 → #4a2a3f → #6a3a5f)
- **Text:** Light Pink (#f0d9e8)
- **Use Case:** Modern, trendy, feminine, creative
- **Best For:** Creative teams, design agencies

## Theme Features

✨ **Dynamic Switching**
- Change themes instantly without page reload
- Smooth transitions between color schemes
- Saves preference to browser localStorage

🎯 **Comprehensive Styling**
- All UI elements respect theme colors
- Cards, buttons, gauges all adapt
- Consistent color system across platform

💾 **Persistent Storage**
- User theme preference saved locally
- Automatically loads preferred theme on page load
- Works across browser sessions

🔄 **Real-time Updates**
- All metrics and alerts use theme colors
- Notification colors adapt to theme
- Modal dialogs match current theme

## CSS Variables Used

```css
--bg-primary: Primary background color
--bg-secondary: Secondary background color
--bg-tertiary: Tertiary background color
--primary-color: Main brand color
--secondary-color: Secondary brand color
--text-primary: Main text color
--text-secondary: Secondary text color
--card-bg: Card background with opacity
--card-border: Card border color
--success-color: Success state color
--warning-color: Warning state color
--danger-color: Danger/error state color
```

## How to Switch Themes

1. Click the **🎨 Theme** button (fixed top-right)
2. Select from 7 available themes
3. Theme changes instantly
4. Your choice is saved automatically

## Extending the Theme System

To add a new theme, add a new CSS rule:

```css
body.theme-newname {
    --bg-primary: #color1;
    --bg-secondary: #color2;
    --bg-tertiary: #color3;
    --primary-color: #color4;
    --secondary-color: #color5;
    --text-primary: #color6;
    --text-secondary: #color7;
    --card-bg: rgba(color, 0.1);
    --card-border: rgba(color, 0.3);
}
```

Then add a theme option button in the HTML:

```html
<div class="theme-option" data-theme="newname" onclick="switchTheme('newname')">🎨 NewName</div>
```

---

**LizzyMonitor Theme System** - Making monitoring beautiful and accessible ✨
