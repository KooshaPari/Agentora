use phenotype_observability::{init_tracer, increment_counter};

fn main() {
    init_tracer("phenotype-event-sourcing-example");
    increment_counter("event.append.example");
    println!("Event-sourcing example ran (tracer/metric stub)");
}
