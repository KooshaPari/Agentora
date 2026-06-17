use crate::domain::entities::{ExecutionStatus, FeatureResult, ScenarioResult, StepResult};
use crate::domain::ports::outbound::ReportWriterPort;
use crate::BddError;
use std::io::Write;

pub struct JUnitReporter<W: Write> {
    package: String,
    writer: W,
}

impl<W: Write> JUnitReporter<W> {
    pub fn new(package: impl Into<String>, writer: W) -> Self {
        Self {
            package: package.into(),
            writer,
        }
    }

    pub fn to_stdout(package: impl Into<String>) -> Self {
        Self::new(package, std::io::stdout())
    }

    fn write_xml_escape(&self, s: &str) -> String {
        s.replace('&', "&amp;")
            .replace('<', "&lt;")
            .replace('>', "&gt;")
            .replace('"', "&quot;")
            .replace('\'', "&apos;")
    }

    fn format_duration(&self, ms: u64) -> String {
        let secs = ms / 1000;
        let nanos = (ms % 1000) * 1_000_000;
        format!("{}.{:09}s", secs, nanos)
    }

    fn write_testcase(&self, scenario: &ScenarioResult, feature_name: &str) -> String {
        let classname = format!("{}.{}", self.package, feature_name);
        let name = self.write_xml_escape(&scenario.name);
        let time = self.format_duration(scenario.duration_ms);

        let mut xml = format!(
            r#"    <testcase classname="{}" name="{}" time="{}">"#,
            classname, name, time
        ));

        match scenario.status {
            ExecutionStatus::Failed => {
                let msg = scenario
                    .error_message
                    .as_ref()
                    .map(|e| self.write_xml_escape(e))
                    .unwrap_or_default();
                xml.push_str(&format!(
                    r#"
      <failure message="{}" type="AssertionError">
        <![CDATA[{}]]>
      </failure>
    </testcase>"#,
                    msg, msg
                ));
            }
            ExecutionStatus::Skipped => {
                xml.push_str(r#"
      <skipped/>
    </testcase>"#);
            }
            _ => {
                xml.push_str("\n    </testcase>");
            }
        }

        xml
    }

    fn generate_junit_xml(&self, result: &FeatureResult) -> String {
        let mut xml = String::from(r#"<?xml version="1.0" encoding="UTF-8"?>"#);

        let test_count = result.scenarios.len();
        let failures = result.failed_scenarios();
        let skipped = result
            .scenarios
            .iter()
            .filter(|s| s.status == ExecutionStatus::Skipped)
            .count();
        let time = self.format_duration(result.duration_ms);
        let timestamp = result.timestamp.format("%Y-%m-%dT%H:%M:%S").to_string();

        xml.push_str(&format!(
            r#"
<testsuite name="{}" tests="{}" failures="{}" skipped="{}" time="{}" timestamp="{}" package="{}">
"#,
            self.write_xml_escape(&result.name),
            test_count,
            failures,
            skipped,
            time,
            timestamp,
            self.package
        ));

        for scenario in &result.scenarios {
            xml.push_str(&self.write_testcase(scenario, &result.name));
            xml.push('\n');
        }

        xml.push_str("</testsuite>\n");
        xml
    }
}

impl<W: Write> ReportWriterPort for JUnitReporter<W> {
    fn write_feature_report(&self, result: &FeatureResult) -> Result<(), BddError> {
        let xml = self.generate_junit_xml(result);
        writeln!(self.writer, "{}", xml).map_err(|e| BddError::ReportError(e.to_string()))?;
        Ok(())
    }

    fn format(&self) -> &str {
        "junit"
    }

    fn flush(&self) -> Result<(), BddError> {
        self.writer
            .flush()
            .map_err(|e| BddError::ReportError(e.to_string()))
    }
}

impl ReportWriterPort for JUnitReporter<std::io::Stdout> {
    fn write_feature_report(&self, result: &FeatureResult) -> Result<(), BddError> {
        let xml = self.generate_junit_xml(result);
        println!("{}", xml);
        Ok(())
    }

    fn format(&self) -> &str {
        "junit"
    }

    fn flush(&self) -> Result<(), BddError> {
        Ok(())
    }
}

#[derive(Debug, thiserror::Error)]
pub enum ReportError {
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),
    #[error("Report error: {0}")]
    ReportError(String),
}

impl From<ReportError> for BddError {
    fn from(e: ReportError) -> Self {
        match e {
            ReportError::Io(e) => BddError::ReportError(e.to_string()),
            ReportError::ReportError(s) => BddError::ReportError(s),
        }
    }
}

impl BddError {
    pub fn report_error(msg: impl Into<String>) -> Self {
        BddError::ReportError(msg.into())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::domain::entities::{ScenarioResult, StepResult};
    use std::io::Cursor;

    fn create_test_feature() -> FeatureResult {
        let mut feature = FeatureResult::new("User Authentication", "Login functionality");
        feature.add_scenario(
            ScenarioResult::new("Successful login")
                .passed()
                .with_duration(150),
        );
        feature.add_scenario(
            ScenarioResult::new("Failed login")
                .failed("Invalid credentials")
                .with_duration(50),
        );
        feature
    }

    #[test]
    fn test_junit_reporter_generates_valid_xml() {
        let feature = create_test_feature();
        let reporter = JUnitReporter::new("com.example.bdd", Cursor::new(Vec::new()));
        let xml = reporter.generate_junit_xml(&feature);

        assert!(xml.contains(r#"<?xml version="1.0" encoding="UTF-8"?>"#));
        assert!(xml.contains(r#"<testsuite name="User Authentication""#));
        assert!(xml.contains(r#"tests="2""#));
        assert!(xml.contains(r#"failures="1""#));
        assert!(xml.contains(r#"<testcase classname="com.example.bdd.User Authentication""#));
        assert!(xml.contains(r#"<failure message="Invalid credentials""#));
    }

    #[test]
    fn test_junit_reporter_write() {
        let feature = create_test_feature();
        let cursor = Cursor::new(Vec::new());
        let reporter = JUnitReporter::new("com.example.bdd", cursor);
        reporter.write_feature_report(&feature).unwrap();
    }

    #[test]
    fn test_xml_escape() {
        let feature = FeatureResult::new("Test <>&\"'", "Description");
        let cursor = Cursor::new(Vec::new());
        let reporter = JUnitReporter::new("pkg", cursor);
        let xml = reporter.generate_junit_xml(&feature);

        assert!(xml.contains("&lt;&gt;&amp;&quot;&apos;"源头"));
    }

    #[test]
    fn test_format_returns_junit() {
        let reporter = JUnitReporter::to_stdout("com.example");
        assert_eq!(reporter.format(), "junit");
    }

    #[test]
    fn test_empty_feature() {
        let feature = FeatureResult::new("Empty", "No scenarios");
        let cursor = Cursor::new(Vec::new());
        let reporter = JUnitReporter::new("pkg", cursor);
        let xml = reporter.generate_junit_xml(&feature);

        assert!(xml.contains(r#"tests="0""#));
        assert!(xml.contains(r#"failures="0""#));
    }

    #[test]
    fn test_skipped_scenario() {
        let mut feature = FeatureResult::new("Test", "Skipped scenario");
        feature.add_scenario(ScenarioResult::new("Skipped test").skipped());
        let cursor = Cursor::new(Vec::new());
        let reporter = JUnitReporter::new("pkg", cursor);
        let xml = reporter.generate_junit_xml(&feature);

        assert!(xml.contains(r#"skipped="1""#));
        assert!(xml.contains("<skipped/>"));
    }

    #[test]
    fn test_step_status_mapping() {
        let mut feature = FeatureResult::new("Steps", "Step level results");
        let mut scenario = ScenarioResult::new("Step test");
        scenario.add_step(StepResult::new("Given", "setup").passed().with_duration(10));
        scenario.add_step(
            StepResult::new("When", "action")
                .failed("Error occurred")
                .with_duration(100),
        );
        scenario.add_step(StepResult::new("Then", "result").skipped());
        feature.add_scenario(scenario);

        let cursor = Cursor::new(Vec::new());
        let reporter = JUnitReporter::new("pkg", cursor);
        let xml = reporter.generate_junit_xml(&feature);

        assert!(xml.contains("failures=\"1\""));
        assert!(xml.contains("skipped=\"1\""));
    }
}
