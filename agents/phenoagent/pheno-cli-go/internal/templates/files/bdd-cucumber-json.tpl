{
  "default": {
    "format": ["progress-bar"],
    "formatOptions": { "snippetInterface": "async-await" },
    "requireModule": ["ts-node/register"],
    "require": ["steps/**/*.ts"],
    "paths": ["features/**/*.feature"]
  },
  "ci": {
    "format": ["json:reports/cucumber-report.json"],
    "formatOptions": { "snippetInterface": "async-await" },
    "requireModule": ["ts-node/register"],
    "require": ["steps/**/*.ts"],
    "paths": ["features/**/*.feature"]
  }
}
