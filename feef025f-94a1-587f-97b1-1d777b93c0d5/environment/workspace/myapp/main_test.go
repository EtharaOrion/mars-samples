package main

import (
	"testing"

	"example.com/mylib"
)

func TestGreet(t *testing.T) {
	cases := []struct {
		name string
		in   string
		want string
	}{
		{"world", "world", "Hello, world"},
		{"empty", "", "Hello, "},
		{"unicode", "みんな", "Hello, みんな"},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			got := mylib.Greet(tc.in)
			if got != tc.want {
				t.Fatalf("Greet(%q) = %q, want %q", tc.in, got, tc.want)
			}
		})
	}
}

func TestFarewell(t *testing.T) {
	got := mylib.Farewell("world")
	want := "Goodbye, world"
	if got != want {
		t.Fatalf("Farewell(world) = %q, want %q", got, want)
	}
}
