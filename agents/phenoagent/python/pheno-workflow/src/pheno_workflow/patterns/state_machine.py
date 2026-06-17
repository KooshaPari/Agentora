"""
State machine pattern for workflows.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass
class Transition:
    """
    State transition.
    """

    from_state: str
    to_state: str
    event: str
    guard: Callable[[Any], bool] | None = None
    action: Callable[[Any], None] | None = None


@dataclass
class State:
    """
    State definition.
    """

    name: str
    on_enter: Callable | None = None
    on_exit: Callable | None = None


class StateMachine:
    """State machine implementation.

    Example:
        # Define states
        sm = StateMachine(initial_state="draft")

        # Add states
        sm.add_state("draft")
        sm.add_state("submitted")
        sm.add_state("approved")
        sm.add_state("rejected")

        # Add transitions
        sm.add_transition("draft", "submitted", "submit")
        sm.add_transition("submitted", "approved", "approve")
        sm.add_transition("submitted", "rejected", "reject")

        # Trigger events
        sm.trigger("submit")
        print(sm.current_state)  # "submitted"
    """

    def __init__(self, initial_state: str):
        self.current_state = initial_state
        self.states: dict[str, State] = {}
        self.transitions: list[Transition] = []

    def add_state(
        self,
        name: str,
        on_enter: Callable | None = None,
        on_exit: Callable | None = None,
    ):
        """
        Add a state.
        """
        self.states[name] = State(
            name=name,
            on_enter=on_enter,
            on_exit=on_exit,
        )

    def add_transition(
        self,
        from_state: str,
        to_state: str,
        event: str,
        guard: Callable[[Any], bool] | None = None,
        action: Callable[[Any], None] | None = None,
    ):
        """
        Add a transition.
        """
        transition = Transition(
            from_state=from_state,
            to_state=to_state,
            event=event,
            guard=guard,
            action=action,
        )
        self.transitions.append(transition)

    def trigger(self, event: str, context: Any | None = None) -> bool:
        """
        Trigger an event.
        """
        # Find matching transition
        transition = self._find_transition(event)
        if not transition:
            return False

        # Check guard
        if transition.guard and not transition.guard(context):
            return False

        # Execute exit callback
        current = self.states.get(self.current_state)
        if current and current.on_exit:
            current.on_exit()

        # Execute transition action
        if transition.action:
            transition.action(context)

        # Change state
        self.current_state = transition.to_state

        # Execute enter callback
        new_state = self.states.get(self.current_state)
        if new_state and new_state.on_enter:
            new_state.on_enter()

        return True

    def _find_transition(self, event: str) -> Transition | None:
        """
        Find transition for event from current state.
        """
        for transition in self.transitions:
            if transition.from_state == self.current_state and transition.event == event:
                return transition
        return None

    def can_trigger(self, event: str, context: Any | None = None) -> bool:
        """
        Check if event can be triggered.
        """
        transition = self._find_transition(event)
        if not transition:
            return False

        if transition.guard:
            return transition.guard(context)

        return True
