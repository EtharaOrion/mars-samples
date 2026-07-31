module example.com/greeter

go 1.23

require example.com/legacy v0.0.0

replace example.com/legacy => ./internal/legacy
