from setuptools import setup, find_packages

setup(
    name='sgfs',
    version='0.1.0b',
    description='Translation layer between Shotgun entities and a file structure.',
    url='http://github.com/westernx/sgfs',
    
    packages=find_packages(exclude=['build*', 'tests*']),
    include_package_data=True,
    
    author='Mike Boers',
    author_email='sgfs@mikeboers.com',
    license='BSD-3',
    
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    
)