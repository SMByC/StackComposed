## Build and Upload:

    python setup.py sdist bdist_wheel
    twine upload --repository-url https://upload.pypi.org/legacy/ dist/*

## PyInstaller:
    
    pyinstaller --onefile --hidden-import=appdirs --hidden-import=packaging.version --hidden-import=packaging.specifiers --hidden-import=packaging.requirements stack_composed.py
