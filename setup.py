import setuptools
from os.path import dirname
from glob import glob

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Package list is autogenerated to be any 'perceval' subfolder containing a __init__.py file
package_list = [dirname(p).replace('\\', '.') for p in glob('perceval/**/__init__.py', recursive=True)]

setuptools.setup(
    name="perceval-quandela",
    version="0.0.1",
    author="Perceval@Quandela.com",
    author_email="Perceval@Quandela.com",
    description="A powerful Quantum Photonic Framework",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Quandela/Perceval",
    project_urls={
        "Documentation": "https://perceval.quandela.net/docs/",
        "Source": "https://github.com/Quandela/Perceval",
        "Tracker": "https://github.com/Quandela/Perceval/issues"
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    packages=package_list,
    install_requires=['sympy', 'numpy', 'scipy', 'tabulate', 'matplotlib', 'quandelibc>=0.5.3', 'multipledispatch',
                      'protobuf>=4.21.2', 'Deprecated', 'requests'],
    setup_requires=["scmver"],
    extras_require={"test": ["pytest", "pytest-cov"]},
    python_requires=">=3.6",
    scmver=True
)
