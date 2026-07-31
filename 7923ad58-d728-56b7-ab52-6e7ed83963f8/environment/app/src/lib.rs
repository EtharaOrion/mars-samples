pub const INPUT: [u64; 8] = [7, 11, 13, 17, 19, 23, 29, 31];

#[cfg(feature = "fast")]
pub fn compute(values: &[u64]) -> u64 {
    let mut acc: u64 = 0;
    for &v in values {
        acc = acc.wrapping_mul(31).wrapping_add(v);
    }
    acc
}

#[cfg(not(feature = "fast"))]
pub fn compute(values: &[u64]) -> u64 {
    let mut acc: u64 = 0;
    for &v in values {
        acc = acc.wrapping_add(v);
    }
    acc
}
