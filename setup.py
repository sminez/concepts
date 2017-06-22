from setuptools import setup, find_packages
import os

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name='concepts',
    author="Innes Anderson-Morrison",
    author_email='innesdmorrison@gmail.com',
    install_requires=[],
    package_dir={'concepts': 'concepts'},
    packages=find_packages(),
    classifiers=[
        'Programming Language :: Python :: 3',
        'Development Status :: 4 - Beta'
    ]
)
