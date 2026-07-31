package mathx

import "testing"

func TestSum(t *testing.T) {
	if got := Sum([]int{3, 7, 11, 13}); got != 34 {
		t.Fatalf("Sum=%d", got)
	}
}

func TestProduct(t *testing.T) {
	if got := Product([]int{3, 7, 11, 13}); got != 3003 {
		t.Fatalf("Product=%d", got)
	}
}
