use star18::{compute, INPUT};

#[test]
fn compute_matches_golden() {
    assert_eq!(compute(&INPUT), 202739307150);
}
