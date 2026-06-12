use agentkit::prelude::{Skill, SkillRegistry, SkillResult};
use agentkit::{Error, Result};
use async_trait::async_trait;
use serde_json::{json, Value};

#[derive(Clone, Debug)]
struct TweetClawWorkflowSkill;

const SOURCE_COLLECTION_JOBS: &[&str] = &[
    "scrape_tweets",
    "search_tweets",
    "search_tweet_replies",
    "follower_export",
    "user_lookup",
    "media_download",
];

const APPROVAL_REQUIRED_JOBS: &[&str] = &[
    "post_tweets",
    "post_tweet_replies",
    "direct_messages",
    "media_upload",
    "monitor_tweets",
    "webhooks",
    "giveaway_draws",
];

#[async_trait]
impl Skill for TweetClawWorkflowSkill {
    fn name(&self) -> &str {
        "tweetclaw_workflow"
    }

    fn description(&self) -> String {
        "Route TweetClaw X/Twitter jobs through source or approval workflows".to_string()
    }

    async fn execute(&self, params: Value) -> Result<SkillResult> {
        let job = params
            .get("job")
            .and_then(Value::as_str)
            .ok_or_else(|| Error::Skill("Missing 'job' parameter".to_string()))?;
        let normalized_job = normalize_job(job);

        if SOURCE_COLLECTION_JOBS.contains(&normalized_job.as_str()) {
            return Ok(SkillResult::success(json!({
                "job": normalized_job,
                "route": "tweetclaw",
                "mode": "source_collection",
                "requires_approval": false,
                "review_notes": [
                    "Keep credentials in host configuration.",
                    "Return source IDs, URLs, metrics, and reviewed notes."
                ]
            })));
        }

        if APPROVAL_REQUIRED_JOBS.contains(&normalized_job.as_str()) {
            return Ok(SkillResult::success(json!({
                "job": normalized_job,
                "route": "tweetclaw",
                "mode": "account_action",
                "requires_approval": true,
                "review_notes": [
                    "Show the exact account-changing action before execution.",
                    "Require operator confirmation before sending the tool call."
                ]
            })));
        }

        Ok(SkillResult::failure(format!(
            "Unsupported TweetClaw workflow job: {job}"
        )))
    }
}

fn normalize_job(job: &str) -> String {
    job.trim()
        .to_ascii_lowercase()
        .split(|character: char| character.is_ascii_whitespace() || character == '-')
        .filter(|part| !part.is_empty())
        .collect::<Vec<_>>()
        .join("_")
}

#[tokio::main]
async fn main() -> Result<()> {
    let mut registry = SkillRegistry::new();
    registry.register(Box::new(TweetClawWorkflowSkill))?;

    let skill = registry
        .get("tweetclaw_workflow")
        .ok_or_else(|| Error::Skill("tweetclaw_workflow was not registered".to_string()))?;

    let source_collection = skill
        .execute(json!({
            "job": "search tweets",
            "query": "agent tools"
        }))
        .await?;
    assert!(source_collection.success);
    assert_eq!(source_collection.data["requires_approval"], false);

    let account_action = skill
        .execute(json!({
            "job": "post---tweet   replies",
            "draft": "Thanks for the feedback."
        }))
        .await?;
    assert!(account_action.success);
    assert_eq!(account_action.data["job"], "post_tweet_replies");
    assert_eq!(account_action.data["requires_approval"], true);

    let rendered = serde_json::to_string_pretty(&json!({
        "source_collection": source_collection.data,
        "approval_gated_action": account_action.data
    }))
    .map_err(|err| Error::Execution(err.to_string()))?;
    println!("{rendered}");

    Ok(())
}
