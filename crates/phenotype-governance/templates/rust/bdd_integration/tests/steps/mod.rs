//! Step definitions for BDD tests
//!
//! Implement the steps referenced in your .feature files.

use phenotype_bdd::{
    StepRegistry, StepContext, StepArgs, Result as BddResult,
    domain::entities::{StepResult, ExecutionStatus},
};

/// Setup the step registry with your domain-specific steps
pub async fn setup_registry() -> BddResult<StepRegistry> {
    let mut registry = StepRegistry::new();

    // Background steps
    registry.given("the system is initialized", |ctx, _| async move {
        ctx.insert("initialized", true)?;
        Ok(())
    }).await?;

    // Given steps
    registry.given("some precondition", |ctx, _| async move {
        ctx.insert("precondition", "met")?;
        Ok(())
    }).await?;

    registry.given("an invalid input", |ctx, _| async move {
        ctx.insert("input_valid", false)?;
        Ok(())
    }).await?;

    registry.given("some data", |ctx, _| async move {
        ctx.insert("data", "test data")?;
        Ok(())
    }).await?;

    registry.given("a complete workflow", |ctx, _| async move {
        ctx.insert("workflow", "complete")?;
        Ok(())
    }).await?;

    // When steps
    registry.when("I perform an action", |ctx, _| async move {
        let initialized: bool = ctx.get("initialized")?.unwrap_or(false);
        let input_valid: bool = ctx.get("input_valid")?.unwrap_or(true);
        
        if initialized && input_valid {
            ctx.insert("action_result", "success")?;
        } else {
            ctx.insert("action_result", "error")?;
            ctx.insert("error_message", "Invalid input or not initialized")?;
        }
        
        Ok(())
    }).await?;

    registry.when("I save the data", |ctx, _| async move {
        let data: String = ctx.get("data")?.unwrap_or_default();
        ctx.insert("saved_data", data)?;
        Ok(())
    }).await?;

    registry.when("I retrieve the data", |ctx, _| async move {
        // Data is already saved in context
        Ok(())
    }).await?;

    registry.when("all steps are executed", |ctx, _| async move {
        ctx.insert("workflow_complete", true)?;
        Ok(())
    }).await?;

    // Then steps
    registry.then("the result should be success", |ctx, _| async move {
        let result: String = ctx.get("action_result")?.unwrap_or_default();
        assert_eq!(result, "success", "Action should succeed");
        Ok(())
    }).await?;

    registry.then("an error should occur", |ctx, _| async move {
        let result: String = ctx.get("action_result")?.unwrap_or_default();
        assert_eq!(result, "error", "Error should occur");
        Ok(())
    }).await?;

    registry.then("the error message should explain the problem", |ctx, _| async move {
        let message: String = ctx.get("error_message")?.unwrap_or_default();
        assert!(!message.is_empty(), "Error message should exist");
        Ok(())
    }).await?;

    registry.then("the retrieved data should match the saved data", |ctx, _| async move {
        let original: String = ctx.get("data")?.unwrap_or_default();
        let saved: String = ctx.get("saved_data")?.unwrap_or_default();
        assert_eq!(original, saved, "Retrieved data should match");
        Ok(())
    }).await?;

    registry.then("the workflow should complete successfully", |ctx, _| async move {
        let complete: bool = ctx.get("workflow_complete")?.unwrap_or(false);
        assert!(complete, "Workflow should complete");
        Ok(())
    }).await?;

    Ok(registry)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_registry_setup() {
        let registry = setup_registry().await.unwrap();
        assert!(!registry.is_empty(), "Registry should have steps");
    }
}
