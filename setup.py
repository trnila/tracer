from setuptools import Extension
from setuptools import setup, find_packages

setup(
        name='tracer',
        packages=find_packages(),
        install_requires='python-ptrace==0.9.1',
        entry_points={
            'console_scripts': ['tracer = tracer.__main__:main']
        },
        ext_modules=[
                Extension(
                        "backtrace",
                        ["backtrace/python.cpp", "backtrace/backtrace.cpp"],
                        libraries=['unwind', 'unwind-x86_64', 'unwind-ptrace'],
                        extra_compile_args=['-std=c++11']
                )
        ]
)
