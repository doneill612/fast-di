from setuptools import setup, find_packages

setup(
    name='fastdi',
    version='0.1.0',
    author='David O\'Neill',
    description='A .NET-like dependency injection framework for FastAPI.',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/doneill612/fast-di',
    package_dir={'': 'src'},
    packages=find_packages(where='src'),
    classifiers=[
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
    ],
    python_requires='>=3.7',
    install_requires=['fastapi', 'pydantic'],
    extras_require={
        'dev': [
            'pytest>=3.7',
        ],
    },
)
