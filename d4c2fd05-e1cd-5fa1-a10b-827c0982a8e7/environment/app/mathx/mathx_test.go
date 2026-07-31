package mathx

import "testing"

func TestCompute(t *testing.T) {
	cases := map[int]int{0: 0, 1: 1, 3: 14, 5: 55, 10: 385}
	for n, want := range cases {
		if got := Compute(n); got != want {
			t.Fatalf("Compute(%d)=%d want %d", n, got, want)
		}
	}
}
