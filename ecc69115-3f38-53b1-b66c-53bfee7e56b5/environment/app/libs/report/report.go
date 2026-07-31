package report

import (
	"fmt"

	"example.com/monorepo/libs/mathx"
)

// Render summarises xs using the mathx library.
func Render(xs []int) string {
	return fmt.Sprintf("sum=%d product=%d", mathx.Sum(xs), mathx.Product(xs))
}
