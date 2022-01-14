.DEFAULT_GOAL := build-pypi

build-pypi: clean
	python setup.py sdist bdist_wheel

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info