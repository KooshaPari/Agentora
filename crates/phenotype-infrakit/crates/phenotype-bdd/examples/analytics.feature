# Analytics Event Tracking
# 
# Traces to: FR-ANALYTICS-001, FR-ANALYTICS-002, FR-ANALYTICS-003

Feature: Analytics Event Tracking
  As an application developer
  I want to track user events
  So that I can understand user behavior

  Background:
    Given the analytics client is initialized
    And the API key is valid

  Scenario: Track a simple event
    When I track event "page_view" with properties:
      | property | value |
      | page     | /home |
      | duration | 5000  |
    Then the event should be queued
    And the event should have timestamp
    And the event should have unique ID

  Scenario: Batch events for efficiency
    Given the batch size is 100
    When I track 50 events
    Then all events should be in queue
    And no flush should have occurred
    
    When I track 60 more events
    Then a flush should occur automatically
    And events should be sent in batch

  Scenario: Identify a user
    When I identify user "user-123" with traits:
      | trait    | value        |
      | name     | John Doe     |
      | plan     | premium      |
    Then an identify event should be queued
    And the event should include user traits

  Scenario: Handle missing API key
    Given the API key is empty
    When I try to track an event
    Then an error should be raised
    And the error message should contain "API key"

  Scenario: Flush events on demand
    Given there are pending events in queue
    When I call flush
    Then all pending events should be sent
    And the queue should be empty

  Scenario: Session management
    When I start a new session
    Then the session ID should be generated
    And all subsequent events should include session ID
    
    When I end the session
    Then the session should be cleared
    And new events should have different session ID

  @integration
  Scenario: Send events to backend
    Given the backend is available
    When I track an event
    And I flush the queue
    Then the event should be received by backend
    And the backend should respond with 200 OK
