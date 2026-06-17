// Benchmark stub
use criterion::{criterion_group, criterion_main};

fn criterion_benchmark(c: &mut criterion::Criterion) {
    c.bench_function(stub, |b| b.iter(|| {}));
}

criterion_group!(benches, criterion_benchmark);
criterion_main!(benches);

