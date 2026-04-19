"""
Setup configuration for price-helper package.

This package can be installed locally for development:
    pip install -e .

Or from the GitHub repository:
    pip install git+https://github.com/Alex-Glebov/project_helper.git
"""
import os
import re

from setuptools import setup, find_packages

# Read version from package __init__.py without importing
here = os.path.abspath(os.path.dirname(__file__))
version_file = os.path.join(here, 'price_helper', '__init__.py')
with open(version_file, 'r', encoding='utf-8') as f:
    version_match = re.search(r'^__version__ = [\'"]([^\'"]*)[\'"]', f.read(), re.M)
    version = version_match.group(1) if version_match else '0.0.0'

# Read README
readme_path = os.path.join(here, 'README.md')
if os.path.exists(readme_path):
    with open(readme_path, 'r', encoding='utf-8') as f:
        long_description = f.read()
else:
    long_description = "Python package for retrieving price data from Feather files"

setup(
    name='price-helper',
    version=version,
    author='Alex Glebov + Claude Code',
    author_email='python@iitsp.com.au',
    description='Python package for retrieving price data from Feather files',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/Alex-Glebov/project_helper',
    packages=find_packages(exclude=['tests', 'tests.*', 'wiki']),
    package_data={
        'price_helper': ['*.py'],
    },
    license='MIT',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
    ],
    python_requires='>=3.8',
    install_requires=[
        'pandas>=1.3.0',
        'pyarrow>=5.0.0',  # Required for feather support
        'pytz>=2021.1',     # Timezone support
    ],
    extras_require={
        'dev': [
            'pytest>=6.0',
            'pytest-cov>=2.0',
        ],
    },
    entry_points={
        'console_scripts': [
            'price-helper=price_helper.cli:main',
        ] if os.path.exists(os.path.join(here, 'price_helper', 'cli.py')) else [],
    },
    include_package_data=True,
    zip_safe=False,
)
