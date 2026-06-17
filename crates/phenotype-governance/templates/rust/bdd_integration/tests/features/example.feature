Feature: Example Domain Logic
  As a user
  I want to perform some action
  So that I can achieve a goal

  Background:
    Given the system is initialized

  Scenario: Successful operation
    Given some precondition
    When I perform an action
    Then the result should be success

  Scenario: Error handling
    Given an invalid input
    When I perform an action
    Then an error should occur
    And the error message should explain the problem

  Scenario: Data persistence
    Given some data
    When I save the data
    And I retrieve the data
    Then the retrieved data should match the saved data

  @integration
  Scenario: End-to-end flow
    Given a complete workflow
    When all steps are executed
    Then the workflow should complete successfully
