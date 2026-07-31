const LABEL = "sum-of-squares";

function compute(n) {
  let total = 0;
  for (let i = 1; i <= n; i++) {
    total += i;
  }
  return total;
}

module.exports = { LABEL, compute, CORE_VERSION: "1.0.0" };
