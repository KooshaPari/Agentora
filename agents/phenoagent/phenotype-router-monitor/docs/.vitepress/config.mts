import { createPhenotypeConfig } from '@phenotype/docs/config'

// Environment-based configuration for GitHub Pages compatibility
const isPagesBuild = process.env.GITHUB_ACTIONS === 'true' || process.env.GITHUB_PAGES === 'true'
const repoName = process.env.GITHUB_REPOSITORY?.split('/')[1] || 'phenodocs'
const docsBase = isPagesBuild ? `/${repoName}/` : '/'

export default createPhenotypeConfig({
  title: 'PhenoDocs',
  description: 'Federation hub for multi-project documentation',
  lang: 'en-US',
  srcDir: 'docs',
  base: docsBase,
  srcDir: 'docs',
  githubOrg: 'KooshaPari',
  githubRepo: repoName,

  nav: [
    { text: 'Guide', link: '/guide/getting-started' },
    { text: 'Architecture', link: '/guide/architecture' },
    { text: 'API', link: '/reference/api' },
    { text: 'Governance', link: '/governance/overview' },
    { text: 'Roadmap', link: '/roadmap/' },
    { text: 'Workspace views', link: '/views/' },
  ],

  themeConfig: {
    logo: '/logo.svg',
    siteTitle: 'PhenoDocs',

    nav: [
      { text: 'Guide', link: '/guide/getting-started' },
      { text: 'Architecture', link: '/guide/architecture' },
      { text: 'API', link: '/reference/api' },
      { text: 'Governance', link: '/governance/overview' },
      { text: 'Roadmap', link: '/roadmap/' },
      { text: 'Workspace views', link: '/views/' }
    ],

    sidebar: {
      '/guide/': [
        {
          text: 'Getting Started',
          items: [
            { text: 'Introduction', link: '/guide/getting-started' },
            { text: 'Architecture', link: '/guide/architecture' },
            { text: 'Full-turn delivery', link: '/guides/full-turn-delivery' }
          ]
        }
      ],
      '/reference/': [
        {
          text: 'Reference',
          items: [
            { text: 'API', link: '/reference/api' }
          ]
        }
      ],
      '/governance/': [
        {
          text: 'Governance',
          items: [
            { text: 'Overview', link: '/governance/overview' },
            { text: 'Stacked PRs', link: '/governance/stacked-prs/' }
          ]
        }
      ],
      '/templates/': [
        {
          text: 'Templates',
          items: [
            { text: 'Release Matrix Template', link: '/templates/release-matrix-template' }
          ]
        }
      ],
      '/roadmap/': [
        {
          text: 'Roadmap',
          items: [
            { text: 'Overview', link: '/roadmap/' }
          ]
        }
      ],
      '/planning/': [
        {
          text: 'Planning',
          items: [
            { text: 'Rich workspace views', link: '/planning/rich-workspace-views' },
            { text: 'Full-turn Next 24', link: '/planning/full-turn-next24-20260326' }
          ]
        }
      ],
      '/views/': [
        {
          text: 'Workspace views',
          items: [
            { text: 'Overview', link: '/views/' },
            { text: 'Changelog (rich)', link: '/views/changelog' },
            { text: 'Commit log', link: '/views/commits' },
            { text: 'WBS & DAG', link: '/views/wbs' }
          ]
        }
      ]
    },

    socialLinks: [
      { icon: 'github', link: `https://github.com/kooshapari/${repoName}` }
    ],

    footer: {
      message: 'Released under the MIT License.',
      copyright: 'Copyright © 2024 Kush Team'
    },

    search: {
      provider: 'local'
    },

    editLink: {
      pattern: `https://github.com/kooshapari/${repoName}/edit/main/docs/:path`,
      text: 'Edit this page on GitHub'
    },

    outline: {
      level: [2, 3],
      label: 'On this page'
    },

    externalLinkIcon: true,
    breadcrumb: true
  },

  overrides: {
    themeConfig: {
      logo: '/logo.svg',
      breadcrumb: true,
    },
    markdown: {
      anchorLinks: true,
    },
  },
})
