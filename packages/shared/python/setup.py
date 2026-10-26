"""
Setup script for brasaland_shared package

Installation:
    pip install -e packages/shared/python
"""
from setuptools import setup, find_packages

setup(
    name="brasaland-shared",
    version="1.0.0",
    description="Paquete compartido transversal para validaciones y lógica de dominio Brasaland",
    author="Brasaland Digital Team",
    author_email="tech@brasaland.com",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        # Sin dependencias externas - solo stdlib
    ],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
