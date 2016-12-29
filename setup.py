from setuptools import setup, find_packages

setup(
        name='tracer',
        packages=find_packages(),
        install_requires='python-ptrace==0.9.1',
        entry_points={
            'console_scripts': ['tracer = tracer.__main__:main']
        }
)
