{
  "name": "{{.RepoName}}-bdd-tests",
  "version": "0.1.0",
  "scripts": {
    "test": "cucumber-js",
    "test:ci": "cucumber-js --format json:reports/cucumber-report.json"
  },
  "devDependencies": {
    "@cucumber/cucumber": "^10.0.0",
    "chai": "^4.3.0",
    "typescript": "^5.0.0",
    "ts-node": "^10.9.0",
    "@types/node": "^20.0.0"
  }
}
