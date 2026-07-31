const LABEL = "sum-of-squares";

function compute(n) {
  let total = 0;
  for (let i = 1; i <= n; i++) {
    total += i * i;
  }
  return total;
}

module.exports = { LABEL, compute, CORE_VERSION: "2.0.0" };
