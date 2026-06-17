[package]
name = "{{.RepoName}}-bdd-tests"
version = "0.1.0"
edition = "2021"

[dependencies]
cucumber = "0.20"
tokio = { version = "1.0", features = ["macros", "rt-multi-thread"] }
uuid = { version = "1.0", features = ["v4"] }

[[test]]
name = "bdd"
harness = false
