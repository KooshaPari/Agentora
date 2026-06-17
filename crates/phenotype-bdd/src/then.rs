//! Then - Assertion phase for BDD tests

pub struct Then<T> {
    state: T,
}

impl<T> Then<T> {
    pub fn new(state: T) -> Self {
        Self { state }
    }

    pub fn state(&self) -> &T {
        &self.state
    }

    pub fn into_state(self) -> T {
        self.state
    }

    /// Assert a condition on the state
    pub fn assert<F>(self, f: F) -> Self
    where
        F: FnOnce(&T) -> bool,
    {
        assert!(f(&self.state), "Assertion failed");
        self
    }
}

impl<T> From<T> for Then<T> {
    fn from(state: T) -> Self {
        Self { state }
    }
}

impl<T> From<crate::When<T>> for Then<T> {
    fn from(when: crate::When<T>) -> Self {
        Self::new(when.into_state())
    }
}
