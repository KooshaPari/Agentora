//! Given - Setup phase for BDD tests

pub struct Given<T> {
    state: T,
}

impl<T> Given<T> {
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

impl<T> From<T> for Given<T> {
    fn from(state: T) -> Self {
        Self { state }
    }
}
