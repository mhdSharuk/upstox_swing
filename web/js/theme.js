/* ═══════════════════════════════════════════════════════════
   THEME MANAGEMENT
   
   Handles light/dark mode theme switching and persistence
   ═══════════════════════════════════════════════════════════ */

const ThemeManager = {
  /**
   * Toggle between light and dark themes
   */
  toggle() {
    const html = document.documentElement;
    const currentTheme = html.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    
    this.setTheme(newTheme);
  },

  /**
   * Set a specific theme
   * @param {string} theme - 'light' or 'dark'
   */
  setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
    this.updateButton(theme);
    console.log(`🎨 Theme changed to: ${theme}`);
  },

  /**
   * Update theme button text and icon
   * @param {string} theme - Current theme
   */
  updateButton(theme) {
    const icon = document.getElementById('theme-icon');
    const text = document.getElementById('theme-text');
    
    if (theme === 'dark') {
      icon.textContent = '☀️';
      text.textContent = 'Light Mode';
    } else {
      icon.textContent = '🌙';
      text.textContent = 'Dark Mode';
    }
  },

  /**
   * Initialize theme from localStorage or default to light
   */
  init() {
    const savedTheme = localStorage.getItem('theme') || 'light';
    this.setTheme(savedTheme);
    console.log(`🎨 Theme initialized: ${savedTheme}`);
  }
};

/**
 * Global function for onclick handler
 */
function toggleTheme() {
  ThemeManager.toggle();
}