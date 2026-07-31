.PHONY: build test clean

build:
	mkdir -p out
	python3 -m calc.buildreport > out/app.txt

test:
	mkdir -p out
	python3 -m unittest discover -s spec -p "test_*.py"
	python3 -m scripts.verify_artifact
	touch out/tests.ok

clean:
	rm -rf out
