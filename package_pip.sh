rm -rf build dist
python setup.py bdist_wheel
twine upload dist/*
