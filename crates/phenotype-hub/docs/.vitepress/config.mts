import { defineConfig } from 'vitepress'

// Environment-based configuration for GitHub Pages compatibility
const isPagesBuild = process.env.GITHUB_ACTIONS === 'true' || process.env.GITHUB_PAGES === 'true'
const repoName = process.env.GITHUB_REPOSITORY?.split('/')[1] || 'phenodocs'
const docsBase = isPagesBuild ? `/${repoName}/` : '/'

const baseConfig = defineConfig({
  title: 'PhenoDocs',
  description: 'Federation hub for multi-project documentation with rich visual elements',
  lang: 'en-US',
  srcDir: 'docs',
  base: docsBase,

  markdown: {
    math: true,
    lineNumbers: true,
    theme: {
      light: 'github-light',
      dark: 'github-dark'
    }
  },

  // Head configuration with enhanced styles
  head: [
    ['link', { rel: 'icon', href: '/favicon.ico' }],
    ['meta', { name: 'theme-color', content: '#3c3c3c' }],
    ['meta', { name: 'og:type', content: 'website' }],
    ['meta', { name: 'og:site_name', content: 'PhenoDocs' }],
    ['meta', { name: 'twitter:card', content: 'summary_large_image' }],
    ['link', { rel: 'preconnect', href: 'https://fonts.googleapis.com' }],
    ['link', { rel: 'preconnect', href: 'https://fonts.gstatic.com', crossorigin: '' }],
    ['link', { href: 'https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&family=Inter:wght@400;500;600;700&display=swap', rel: 'stylesheet' }],
    ['style', {}, `
      :root {
        --vp-font-family-base: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        --vp-font-family-mono: 'JetBrains Mono', monospace;
      }
      
      /* GIF Demo Container */
      .gif-demo {
        border-radius: 8px;
        overflow: hidden;
        border: 1px solid var(--vp-c-border);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        margin: 16px 0;
      }
      
      .gif-demo img {
        max-width: 100%;
        height: auto;
        display: block;
      }
      
      .gif-caption {
        padding: 12px 16px;
        background: var(--vp-c-bg-soft);
        font-size: 14px;
        color: var(--vp-c-text-2);
        border-top: 1px solid var(--vp-c-border);
      }
      
      /* User Journey Step Cards */
      .journey-step {
        border-left: 4px solid var(--vp-c-brand);
        padding-left: 16px;
        margin-bottom: 24px;
      }
      
      .journey-step-number {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 28px;
        height: 28px;
        border-radius: 50%;
        background: var(--vp-c-brand);
        color: white;
        font-weight: 600;
        font-size: 14px;
        margin-right: 12px;
      }
      
      /* Traceability Links */
      .trace-link {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 2px 8px;
        border-radius: 4px;
        background: var(--vp-c-brand-soft);
        color: var(--vp-c-brand);
        font-size: 12px;
        font-weight: 500;
        text-decoration: none;
        transition: all 0.2s;
      }
      
      .trace-link:hover {
        background: var(--vp-c-brand);
        color: white;
      }
      
      /* Code Preview Cards */
      .code-preview {
        border-radius: 8px;
        overflow: hidden;
        margin: 16px 0;
      }
      
      .code-preview-header {
        padding: 12px 16px;
        background: var(--vp-c-bg-soft);
        border-bottom: 1px solid var(--vp-c-border);
        display: flex;
        align-items: center;
        justify-content: space-between;
      }
      
      .code-preview-title {
        font-size: 14px;
        font-weight: 500;
        color: var(--vp-c-text-1);
      }
      
      /* Feature Comparison Grid */
      .feature-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
        gap: 16px;
        margin: 24px 0;
      }
      
      .feature-card {
        border: 1px solid var(--vp-c-border);
        border-radius: 8px;
        padding: 16px;
        background: var(--vp-c-bg-soft);
      }
      
      .feature-card h4 {
        margin: 0 0 8px 0;
        font-size: 16px;
      }
      
      .feature-card p {
        margin: 0;
        font-size: 14px;
        color: var(--vp-c-text-2);
      }
      
      /* AgilePlus Traceability Badges */
      .agileplus-badge {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
      }
      
      .agileplus-spec {
        background: #dbeafe;
        color: #1e40af;
      }
      
      .agileplus-test {
        background: #dcfce7;
        color: #166534;
      }
      
      .agileplus-code {
        background: #fce7f3;
        color: #9d174d;
      }
      
      /* Mermaid Diagram Container */
      .mermaid {
        background: var(--vp-c-bg);
        border-radius: 8px;
        padding: 16px;
      }
      
      /* Video Embed Container */
      .video-embed {
        position: relative;
        padding-bottom: 56.25%;
        height: 0;
        overflow: hidden;
        border-radius: 8px;
        margin: 16px 0;
      }
      
      .video-embed iframe {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        border: 0;
      }
    `]
  ],

  themeConfig: {
    nav: [
      { text: 'Home', link: '/' },
      { text: 'Guide', link: '/guide/' },
      { text: 'API', link: '/api/' },
      { text: 'GitHub', link: 'https://github.com/KooshaPari/phenodocs' }
    ],

    sidebar: {
      '/guide/': [
        {
          text: 'Getting Started',
          items: [
            { text: 'Introduction', link: '/guide/' },
            { text: 'Installation', link: '/guide/installation' },
            { text: 'Quick Start', link: '/guide/quickstart' }
          ]
        },
        {
          text: 'Core Concepts',
          items: [
            { text: 'Architecture', link: '/guide/architecture' },
            { text: 'Configuration', link: '/guide/configuration' },
            { text: 'Extensions', link: '/guide/extensions' }
          ]
        }
      ]
    },

    socialLinks: [
      { icon: 'github', link: 'https://github.com/KooshaPari/phenodocs' }
    ],

    search: {
      provider: 'local'
    }
  },

  vite: {
    plugins: [],
    optimizeDeps: {
      include: ['mermaid']
    }
  }
})

export default baseConfig
