//! When - Action phase for BDD tests

pub struct When<T> {
    state: T,
}

impl<T> When<T> {
    pub fn new(state: T) -> Self {
        Self { state }
    }

    pub fn state(&self) -> &T {
        &self.state
    }

    pub fn into_state(self) -> T {
        self.state
    }
}

impl<T> From<T> for When<T> {
    fn from(state: T) -> Self {
        Self { state }
    }
}

impl<T> From<crate::Given<T>> for When<T> {
    fn from(given: crate::Given<T>) -> Self {
        Self::new(given.into_state())
    }
}
