# HTTP Client Behavior
#
# Traces to: FR-HTTP-001, FR-HTTP-002, FR-HTTP-003

Feature: HTTP Client Operations
  As a developer
  I want to make HTTP requests
  So that I can interact with external APIs

  Background:
    Given the HTTP client is configured
    And the base URL is "https://api.example.com"

  Scenario: Successful GET request
    When I send a GET request to "/users"
    Then the response status should be 200
    And the response should have content type "application/json"
    And the response body should contain users

  Scenario: POST request with JSON body
    Given I have a JSON payload:
      """json
      {
        "name": "John Doe",
        "email": "john@example.com"
      }
      """
    When I send a POST request to "/users" with the payload
    Then the response status should be 201
    And the response should contain created user ID

  Scenario: Handle 404 Not Found
    When I send a GET request to "/nonexistent"
    Then the response status should be 404
    And the error should be handled gracefully

  Scenario: Handle server errors (5xx)
    Given the server returns 500 Internal Server Error
    When I send a GET request to "/error"
    Then the response status should be 500
    And the client should report server error

  Scenario: Request timeout
    Given the request timeout is 1 second
    And the server takes 5 seconds to respond
    When I send a GET request to "/slow"
    Then a timeout error should occur
    And the error message should contain "timeout"

  Scenario: Retry on failure
    Given the retry policy is configured with 3 attempts
    And the server fails twice then succeeds
    When I send a GET request to "/flaky"
    Then the request should succeed on third attempt
    And the client should have made 3 requests

  Scenario: Request with headers
    When I send a GET request to "/protected" with headers:
      | header        | value           |
      | Authorization | Bearer token123 |
      | Accept        | application/json |
    Then the request should include those headers
    And the response status should be 200

  Scenario: Response body parsing
    When I send a GET request to "/users/1"
    Then I should be able to parse response as JSON
    And the parsed data should have field "id"
    And the parsed data should have field "name"

  @mock
  Scenario: Mock HTTP client for testing
    Given the mock client is configured
    And the mock returns 200 for "/test"
    When I send a GET request to "/test"
    Then the response status should be 200
    And the mock should record the request
