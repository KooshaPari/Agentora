use super::*;

fn make_args(since: Option<&str>, event_type: Option<&str>, actor: Option<&str>) -> EventsArgs {
    EventsArgs {
        feature: None,
        since: since.map(str::to_string),
        event_type: event_type.map(str::to_string),
        actor: actor.map(str::to_string),
        entity_type: None,
        format: EventOutputFormat::Table,
        limit: 50,
    }
}

#[test]
fn test_parse_since_minutes() {
    let dt = parse_since("30m");
    assert!(dt.is_some());
    let elapsed = Utc::now() - dt.unwrap();
    assert!(elapsed.num_minutes() >= 29 && elapsed.num_minutes() <= 31);
}

#[test]
fn test_parse_since_hours() {
    let dt = parse_since("2h");
    assert!(dt.is_some());
    let elapsed = Utc::now() - dt.unwrap();
    assert!(elapsed.num_hours() >= 1 && elapsed.num_hours() <= 3);
}

#[test]
fn test_parse_since_days() {
    let dt = parse_since("7d");
    assert!(dt.is_some());
    let elapsed = Utc::now() - dt.unwrap();
    assert!(elapsed.num_days() >= 6 && elapsed.num_days() <= 8);
}

#[test]
fn test_parse_since_iso_date() {
    let dt = parse_since("2025-03-01");
    assert!(dt.is_some());
}

#[test]
fn test_parse_since_invalid() {
    assert!(parse_since("bogus").is_none());
}

#[test]
fn test_filter_no_filters() {
    let events = load_events_stub();
    let args = make_args(None, None, None);
    let result = filter_events(&events, &args);
    assert_eq!(result.len(), events.len());
}

#[test]
fn test_filter_by_actor() {
    let events = load_events_stub();
    let args = make_args(None, None, Some("agileplus"));
    let result = filter_events(&events, &args);
    assert_eq!(result.len(), 1);
    assert_eq!(result[0].actor, "agileplus");
}

#[test]
fn test_filter_by_event_type() {
    let events = load_events_stub();
    let args = make_args(None, Some("state_changed"), None);
    let result = filter_events(&events, &args);
    assert_eq!(result.len(), 2);
    assert!(result.iter().all(|e| e.event_type == "state_changed"));
}

#[test]
fn test_filter_limit() {
    let events = load_events_stub();
    let mut args = make_args(None, None, None);
    args.limit = 2;
    let result = filter_events(&events, &args);
    assert_eq!(result.len(), 2);
}

#[test]
fn test_render_table_empty() {
    let out = render_table(&[]);
    assert!(out.contains("No events found"));
}

#[test]
fn test_render_table_nonempty() {
    let events = load_events_stub();
    let out = render_table(&events[..1]);
    assert!(out.contains("feature_created"));
    assert!(out.contains("agileplus"));
}

#[test]
fn test_render_json() {
    let events = load_events_stub();
    let json = render_json(&events[..1]).unwrap();
    assert!(json.contains("feature_created"));
    let parsed: serde_json::Value = serde_json::from_str(&json).unwrap();
    assert!(parsed.is_array());
}

#[test]
fn test_render_jsonl() {
    let events = load_events_stub();
    let jsonl = render_jsonl(&events[..2]).unwrap();
    let lines: Vec<&str> = jsonl.trim_end().split('\n').collect();
    assert_eq!(lines.len(), 2);
    for line in lines {
        let v: serde_json::Value = serde_json::from_str(line).unwrap();
        assert!(v.is_object());
    }
}

#[test]
fn test_run_events_table_does_not_err() {
    let args = EventsArgs {
        feature: None,
        since: None,
        event_type: None,
        actor: None,
        entity_type: None,
        format: EventOutputFormat::Table,
        limit: 10,
    };
    assert!(run_events(args).is_ok());
}

#[test]
fn test_run_events_json_does_not_err() {
    let args = EventsArgs {
        feature: None,
        since: None,
        event_type: None,
        actor: None,
        entity_type: None,
        format: EventOutputFormat::Json,
        limit: 10,
    };
    assert!(run_events(args).is_ok());
}
