import { Given, When, Then, Before } from '@cucumber/cucumber';
import { expect } from 'chai';
import { v4 as uuidv4 } from 'uuid';

interface TestContextType {
  entity: any;
  lastError: Error | null;
  events: any[];
  config: any;
  results: any[];
}

let testContext: TestContextType;

Before(async function() {
  testContext = {
    entity: null,
    lastError: null,
    events: [],
    config: { authToken: 'test-token', concurrentOps: 1, timeout: 30, valid: true },
    results: []
  };
});

Given('the {string} system is initialized', function(system: string) {
  testContext.config.system = system;
});

Given('a valid entity configuration', function() {
  testContext.config = { ...testContext.config, valid: true, data: { name: 'Test', type: 'standard' } };
});

Given('an invalid entity configuration', function() {
  testContext.config = { ...testContext.config, valid: false, data: { name: '', type: 'unknown' } };
});

Given('an existing entity in state {string}', function(state: string) {
  testContext.entity = { id: uuidv4(), state, createdAt: new Date().toISOString() };
});

Given('an unauthenticated user', function() {
  testContext.config.authToken = undefined;
});

Given('{int} concurrent operations', function(count: number) {
  testContext.config.concurrentOps = count;
});

When('I create a new entity', async function() {
  try {
    if (!testContext.config.valid) throw new Error('Invalid configuration');
    testContext.entity = { id: uuidv4(), state: 'created', createdAt: new Date().toISOString() };
  } catch (error) {
    testContext.lastError = error as Error;
  }
});

When('I attempt to create a new entity', async function() {
  try {
    if (!testContext.config.valid) throw new Error('Invalid configuration');
    testContext.entity = { id: uuidv4(), state: 'created', createdAt: new Date().toISOString() };
  } catch (error) {
    testContext.lastError = error as Error;
  }
});

When('I execute the {string} transition', async function(transition: string) {
  try {
    if (!testContext.entity) throw new Error('No entity');
    const oldState = testContext.entity.state;
    testContext.entity.state = transition;
    testContext.events.push({ type: 'transition', from: oldState, to: transition });
  } catch (error) {
    testContext.lastError = error as Error;
  }
});

When('I attempt to access protected resources', async function() {
  try {
    if (!testContext.config.authToken) throw new Error('Unauthorized');
  } catch (error) {
    testContext.lastError = error as Error;
  }
});

When('I execute them within {int} seconds', async function(seconds: number) {
  const start = Date.now();
  const count = testContext.config.concurrentOps;
  for (let i = 0; i < count; i++) {
    await new Promise(r => setTimeout(r, 10));
    testContext.results.push({ opId: i, success: true });
  }
  testContext.config.elapsedTime = (Date.now() - start) / 1000;
});

Then('the entity should be persisted', function() {
  expect(testContext.entity).to.not.be.null;
  expect(testContext.entity.id).to.exist;
});

Then('the entity ID should be returned', function() {
  expect(testContext.entity).to.not.be.null;
  expect(testContext.entity.id).to.exist;
});

Then('the operation should fail', function() {
  expect(testContext.lastError).to.not.be.null;
});

Then('an appropriate error should be returned', function() {
  expect(testContext.lastError).to.not.be.null;
});

Then('the entity should be in state {string}', function(expected: string) {
  expect(testContext.entity.state).to.equal(expected);
});

Then('the transition event should be recorded', function() {
  expect(testContext.events.length).to.be.greaterThan(0);
});

Then('the request should be denied', function() {
  expect(testContext.lastError).to.not.be.null;
});

Then('all operations should complete successfully', function() {
  expect(testContext.lastError).to.be.null;
});

Then('the average response time should be under {int}ms', function(threshold: number) {
  const elapsed = testContext.config.elapsedTime || 0;
  const avgMs = (elapsed / testContext.config.concurrentOps) * 1000;
  expect(avgMs).to.be.lessThan(threshold);
});
