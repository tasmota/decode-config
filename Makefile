.DEFAULT_GOAL := build-pypi

build-pypi: clean
	python setup.py sdist bdist_wheel

docker:
	docker build --tag tasmota/decode-config .

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
