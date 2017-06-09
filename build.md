## Clean

Warning, this will remove all the changes and update to the latest head

    hg up -C

## Build a documentation

    mkdocs build --clean --site-dir /home/xavier/Projects/smbyc/smbyc.bitbucket.org/stackcomposed/

## Build and Upload:

    python setup.py sdist bdist_wheel
    twine upload dist/*
