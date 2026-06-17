"""
BDD Step Definitions for Python (behave)
"""

from behave import given, when, then
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
import time

@dataclass
class TestContext:
    entity: Optional[Dict[str, Any]] = None
    last_error: Optional[Exception] = None
    events: List[Dict[str, Any]] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)
    results: List[Any] = field(default_factory=list)

@given('the {system} system is initialized')
def step_system_initialized(context, system: str):
    context.test.config['system'] = system

@given('a valid entity configuration')
def step_valid_config(context):
    context.test.config.update({'valid': True, 'data': {'name': 'Test', 'type': 'standard'}})

@given('an invalid entity configuration')
def step_invalid_config(context):
    context.test.config.update({'valid': False, 'data': {'name': '', 'type': 'unknown'}})

@given('an existing entity in state "{state}"')
def step_entity_in_state(context, state: str):
    context.test.entity = {'id': str(uuid.uuid4()), 'state': state, 'created_at': datetime.now().isoformat()}

@given('an unauthenticated user')
def step_unauthenticated(context):
    context.test.config['auth_token'] = None

@given('{count:d} concurrent operations')
def step_concurrent_operations(context, count: int):
    context.test.config['concurrent_ops'] = count

@when('I create a new entity')
def step_create_entity(context):
    try:
        if not context.test.config.get('valid', True):
            raise ValueError("Invalid configuration")
        context.test.entity = {'id': str(uuid.uuid4()), 'state': 'created', 'created_at': datetime.now().isoformat()}
    except Exception as e:
        context.test.last_error = e

@when('I attempt to create a new entity')
def step_attempt_create(context):
    step_create_entity(context)

@when('I execute the "{transition}" transition')
def step_execute_transition(context, transition: str):
    try:
        if not context.test.entity:
            raise RuntimeError("No entity")
        old_state = context.test.entity['state']
        context.test.entity['state'] = transition
        context.test.events.append({'type': 'transition', 'from': old_state, 'to': transition})
    except Exception as e:
        context.test.last_error = e

@when('I attempt to access protected resources')
def step_access_protected(context):
    try:
        if not context.test.config.get('auth_token'):
            raise PermissionError("Unauthorized")
    except Exception as e:
        context.test.last_error = e

@when('I execute them within {seconds:d} seconds')
def step_execute_within(context, seconds: int):
    start = time.time()
    count = context.test.config.get('concurrent_ops', 1)
    for i in range(count):
        time.sleep(0.01)
        context.test.results.append({'op_id': i, 'success': True})
    context.test.config['elapsed_time'] = time.time() - start

@then('the entity should be persisted')
def step_entity_persisted(context):
    assert context.test.entity is not None
    assert 'id' in context.test.entity

@then('the entity ID should be returned')
def step_entity_id_returned(context):
    assert context.test.entity is not None
    assert context.test.entity.get('id')

@then('the operation should fail')
def step_operation_failed(context):
    assert context.test.last_error is not None

@then('an appropriate error should be returned')
def step_appropriate_error(context):
    assert context.test.last_error is not None

@then('the entity should be in state "{expected}"')
def step_entity_state(context, expected: str):
    assert context.test.entity is not None
    assert context.test.entity.get('state') == expected

@then('the transition event should be recorded')
def step_transition_recorded(context):
    assert len(context.test.events) > 0

@then('the request should be denied')
def step_request_denied(context):
    assert context.test.last_error is not None
    assert isinstance(context.test.last_error, PermissionError)

@then('all operations should complete successfully')
def step_all_success(context):
    assert context.test.last_error is None

@then('the average response time should be under {threshold:d}ms')
def step_response_time(context, threshold: int):
    elapsed = context.test.config.get('elapsed_time', 0)
    avg_ms = (elapsed / max(context.test.config.get('concurrent_ops', 1), 1)) * 1000
    assert avg_ms < threshold
