//! FR-SDK-79: DTO round-trip + port smoke (Phase B).

use phenotype_agent_contracts::{
    AgentMessage, EvalGardenPort, EvalHookRef, EvidenceLabel, InMemoryScheduler, MessageRole,
    ObservabilityPort, RecordingEvalGarden, RunStatus, SchedulerQueuePort, UnconfiguredObservability,
};
use serde_json::json;

#[test]
fn agent_message_roundtrip_snake_case() {
    let msg = AgentMessage {
        role: MessageRole::User,
        content: "hello".into(),
        id: Some("m1".into()),
        tool_call_id: None,
    };
    let raw = serde_json::to_string(&msg).unwrap();
    assert!(raw.contains("\"role\":\"user\""));
    assert!(raw.contains("\"content\":\"hello\""));
    let back: AgentMessage = serde_json::from_str(&raw).unwrap();
    assert_eq!(back, msg);
}

#[test]
fn evidence_label_wire_live_verified() {
    let hook = EvalHookRef {
        garden_run_id: None,
        evidence_label: EvidenceLabel::LiveVerified,
        suite: Some("mmlu-pro".into()),
        task_id: Some("t1".into()),
    };
    let raw = serde_json::to_string(&hook).unwrap();
    assert!(raw.contains("live verified"));
    let back: EvalHookRef = serde_json::from_str(&raw).unwrap();
    assert_eq!(back.evidence_label, EvidenceLabel::LiveVerified);
}

#[tokio::test]
async fn scheduler_enqueue_poll_cancel() {
    let sched = InMemoryScheduler::new();
    let handle = sched.enqueue(json!({"task": "dh-t1"})).await.unwrap();
    assert_eq!(handle.status, RunStatus::Queued);
    let polled = sched.poll(&handle.run_id).await.unwrap();
    assert_eq!(polled.run_id, handle.run_id);
    sched.cancel(&handle.run_id).await.unwrap();
    let done = sched.poll(&handle.run_id).await.unwrap();
    assert_eq!(done.status, RunStatus::Cancelled);
}

#[tokio::test]
async fn scheduler_poll_unknown_fails_loud() {
    let sched = InMemoryScheduler::new();
    let err = sched.poll("missing").await.unwrap_err();
    assert!(err.to_string().contains("unknown run_id"));
}

#[tokio::test]
async fn observability_unconfigured_fails_loud() {
    let obs = UnconfiguredObservability;
    let err = obs.flush().await.unwrap_err();
    assert!(err.to_string().contains("unconfigured"));
}

#[tokio::test]
async fn eval_garden_records_hook() {
    let garden = RecordingEvalGarden::new();
    garden
        .attach(EvalHookRef {
            garden_run_id: Some("g1".into()),
            evidence_label: EvidenceLabel::Reported,
            suite: None,
            task_id: None,
        })
        .await
        .unwrap();
    assert_eq!(garden.hooks().unwrap().len(), 1);
}
