## Build and Upload:

    python setup.py sdist bdist_wheel
    twine upload dist/*

## PyInstaller:
    
    pyinstaller --onefile --hidden-import=appdirs --hidden-import=packaging.version --hidden-import=packaging.specifiers --hidden-import=packaging.requirements stack_composed.py
