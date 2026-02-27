# setup.py
from setuptools import setup, find_packages

setup(
    name='adubacao-cerrado',
    version='1.0.0',
    packages=find_packages(),
    install_requires=[
        'pandas>=1.0',
        'openpyxl>=3.0',
    ],
    entry_points={
        'console_scripts': [
            'adubacao=adubacao.cli:main',
        ],
    },
    author='Seu Nome',
    description='Calculadora de adubação baseada nos manuais do Cerrado',
    python_requires='>=3.8',
)