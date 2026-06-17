//! Generic finite state machine with transition guards and callbacks.

use std::collections::HashMap;
use std::fmt;
use std::sync::{Arc, RwLock};
use thiserror::Error;

/// Callback type for state enter/exit hooks.
type StateCallback = Arc<dyn Fn(&str) + Send + Sync>;

/// Guard function type for conditional transitions.
type TransitionGuard = Box<dyn Fn(&str, &str) -> bool + Send + Sync>;

/// Errors that can occur during state machine operations.
#[derive(Debug, Clone, Error)]
pub enum StateMachineError {
    #[error("invalid transition: no transition from '{from}' on event '{event}'")]
    InvalidTransition { from: String, event: String },

    #[error("transition from '{from}' on '{event}' rejected by guard")]
    GuardRejected { from: String, event: String },

    #[error("unknown state: '{0}'")]
    UnknownState(String),

    #[error("builder error: {0}")]
    BuildError(String),
}

/// Result type for state machine operations.
pub type Result<T> = std::result::Result<T, StateMachineError>;

/// A transition definition with optional guard.
struct Transition {
    to: String,
    guard: Option<TransitionGuard>,
}

/// A generic finite state machine.
pub struct StateMachine {
    current: RwLock<String>,
    transitions: HashMap<(String, String), Transition>,
    on_enter: HashMap<String, Vec<StateCallback>>,
    on_exit: HashMap<String, Vec<StateCallback>>,
}

impl Default for StateMachine {
    fn default() -> Self {
        Self::new()
    }
}

impl StateMachine {
    /// Create a new empty state machine.
    pub fn new() -> Self {
        Self {
            current: RwLock::new(String::new()),
            transitions: HashMap::new(),
            on_enter: HashMap::new(),
            on_exit: HashMap::new(),
        }
    }

    /// Get the current state.
    pub fn current(&self) -> String {
        self.current.read().unwrap().clone()
    }

    /// Send an event to the state machine.
    pub fn send(&self, event: &str) -> Result<String> {
        let mut current = self.current.write().unwrap();
        let key = (current.clone(), event.to_string());

        let transition =
            self.transitions
                .get(&key)
                .ok_or_else(|| StateMachineError::InvalidTransition {
                    from: current.clone(),
                    event: event.to_string(),
                })?;

        if let Some(guard) = &transition.guard {
            if !guard(&current, event) {
                return Err(StateMachineError::GuardRejected {
                    from: current.clone(),
                    event: event.to_string(),
                });
            }
        }

        // Fire on_exit callbacks for current state.
        if let Some(cbs) = self.on_exit.get(current.as_str()) {
            for cb in cbs {
                cb(&current);
            }
        }

        // Perform the transition.
        let new_state = transition.to.clone();
        *current = new_state.clone();
        drop(current);

        // Fire on_enter callbacks for new state.
        if let Some(cbs) = self.on_enter.get(new_state.as_str()) {
            for cb in cbs {
                cb(&new_state);
            }
        }

        Ok(new_state)
    }

    /// Check if an event can be sent from the current state.
    pub fn can_send(&self, event: &str) -> bool {
        let current = self.current.read().unwrap();
        let key = (current.clone(), event.to_string());
        if let Some(transition) = self.transitions.get(&key) {
            if let Some(guard) = &transition.guard {
                return guard(&current, event);
            }
            return true;
        }
        false
    }

    /// List all events available from the current state.
    pub fn available_events(&self) -> Vec<String> {
        let current = self.current.read().unwrap();
        self.transitions
            .iter()
            .filter(|((from, _), _)| from == &*current)
            .map(|((_, event), _)| event.clone())
            .collect()
    }

    /// Check if in a specific state.
    pub fn is_in(&self, state: &str) -> bool {
        self.current() == state
    }
}

impl fmt::Debug for StateMachine {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("StateMachine")
            .field("current", &self.current())
            .field("states", &self.transitions.len())
            .finish()
    }
}

/// Builder for constructing state machines.
pub struct StateMachineBuilder {
    initial: String,
    transitions: HashMap<(String, String), Transition>,
    on_enter: HashMap<String, Vec<StateCallback>>,
    on_exit: HashMap<String, Vec<StateCallback>>,
}

impl StateMachineBuilder {
    /// Create a new builder with the specified initial state.
    pub fn new(initial: &str) -> Self {
        Self {
            initial: initial.to_string(),
            transitions: HashMap::new(),
            on_enter: HashMap::new(),
            on_exit: HashMap::new(),
        }
    }

    /// Add a transition from one state to another on an event.
    pub fn transition(mut self, from: &str, event: &str, to: &str) -> Self {
        self.transitions.insert(
            (from.to_string(), event.to_string()),
            Transition {
                to: to.to_string(),
                guard: None,
            },
        );
        self
    }

    /// Add a guarded transition.
    pub fn guarded_transition<F>(
        mut self,
        from: &str,
        event: &str,
        to: &str,
        guard: F,
    ) -> Self
    where
        F: Fn(&str, &str) -> bool + Send + Sync + 'static,
    {
        self.transitions.insert(
            (from.to_string(), event.to_string()),
            Transition {
                to: to.to_string(),
                guard: Some(Box::new(guard)),
            },
        );
        self
    }

    /// Add an on-enter callback for a state.
    pub fn on_enter<F>(mut self, state: &str, callback: F) -> Self
    where
        F: Fn(&str) + Send + Sync + 'static,
    {
        self.on_enter
            .entry(state.to_string())
            .or_default()
            .push(Arc::new(callback));
        self
    }

    /// Add an on-exit callback for a state.
    pub fn on_exit<F>(mut self, state: &str, callback: F) -> Self
    where
        F: Fn(&str) + Send + Sync + 'static,
    {
        self.on_exit
            .entry(state.to_string())
            .or_default()
            .push(Arc::new(callback));
        self
    }

    /// Build the state machine.
    pub fn build(self) -> Result<StateMachine> {
        if self.initial.is_empty() {
            return Err(StateMachineError::BuildError(
                "Initial state cannot be empty".to_string(),
            ));
        }

        let mut sm = StateMachine::new();
        *sm.current.write().unwrap() = self.initial;
        sm.transitions = self.transitions;
        sm.on_enter = self.on_enter;
        sm.on_exit = self.on_exit;
        Ok(sm)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::{AtomicUsize, Ordering};

    fn traffic_light() -> StateMachine {
        StateMachineBuilder::new("red")
            .transition("red", "next", "green")
            .transition("green", "next", "yellow")
            .transition("yellow", "next", "red")
            .build()
            .unwrap()
    }

    #[test]
    fn test_basic_transitions() {
        let sm = traffic_light();
        assert_eq!(sm.current(), "red");
        sm.send("next").unwrap();
        assert_eq!(sm.current(), "green");
        sm.send("next").unwrap();
        assert_eq!(sm.current(), "yellow");
    }

    #[test]
    fn test_invalid_transition() {
        let sm = traffic_light();
        let err = sm.send("invalid").unwrap_err();
        assert!(matches!(err, StateMachineError::InvalidTransition { .. }));
    }

    #[test]
    fn test_can_send() {
        let sm = traffic_light();
        assert!(sm.can_send("next"));
        assert!(!sm.can_send("invalid"));
    }

    #[test]
    fn test_on_enter_callback() {
        let count = Arc::new(AtomicUsize::new(0));
        let c = count.clone();
        let sm = StateMachineBuilder::new("a")
            .transition("a", "go", "b")
            .on_enter("b", move |_| {
                c.fetch_add(1, Ordering::SeqCst);
            })
            .build()
            .unwrap();
        sm.send("go").unwrap();
        assert_eq!(count.load(Ordering::SeqCst), 1);
    }
}
