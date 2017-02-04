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
            "tracer.backtrace.libunwind",
            ["tracer/backtrace/libunwind/python.cpp", "tracer/backtrace/libunwind/backtrace.cpp"],
            libraries=['unwind', 'unwind-generic', 'unwind-ptrace'],
            extra_compile_args=['-std=c++11']
        )
    ]
)
