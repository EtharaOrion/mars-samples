package mathx

// Sum returns the sum of xs.
func Sum(xs []int) int {
	s := 0
	for _, x := range xs {
		s += x
	}
	return s
}

// Product returns the product of xs.
func Product(xs []int) int {
	p := 1
	for _, x := range xs {
		p *= x
	}
	return p
}
