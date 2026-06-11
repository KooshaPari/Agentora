//! `agent-platform-tests` — integration tests live here as a library so
//! they can be reused from outside the crate (e.g. doctests, fuzz harnesses).

#[cfg(test)]
mod tests {
    #[test]
    fn scaffold_is_alive() {
        // The boundary exists as soon as a test references the core, ports,
        // and adapters together. Real assertions land with the first adapter.
    }
}
