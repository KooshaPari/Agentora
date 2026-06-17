package bdd_test

import (
	"testing"

	"github.com/cucumber/godog"
)

func TestBDD(t *testing.T) {
	opts := godog.Options{Format: "pretty", Paths: []string{"../features"}}
	suite := godog.TestSuite{ScenarioInitializer: InitializeScenario, Options: &opts}
	if status := suite.Run(); status != 0 {
		t.Fatalf("BDD test suite failed with status %d", status)
	}
}
