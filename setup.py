import sys

from setuptools import setup


with open('requirements.txt') as f:
    requirements = f.read().splitlines()
with open('README.rst') as f:
    readme = f.read()

if sys.version_info[:2] < (2, 7):
    requirements.append('argparse')

setup(
    name='maildump',
    version='1.0-dev',
    description='An SMTP server that makes all received mails accessible via a web interface and REST API.',
    long_description=readme,
    url='https://github.com/ThiefMaster/maildump',
    download_url='https://github.com/ThiefMaster/maildump',
    author='Adrian Mönnich',
    author_email='adrian@planetcoding.net',
    license='MIT',
    zip_safe=False,
    include_package_data=True,
    packages=('maildump', 'maildump_runner'),
    entry_points={
        'console_scripts': [
            'maildump = maildump_runner.main:main',
        ],
    },
    python_requires='>= 3.6',
    install_requires=requirements,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Environment :: No Input/Output (Daemon)',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: MIT License',
        'Topic :: Communications :: Email',
        'Topic :: Software Development',
        'Topic :: System :: Networking',
        'Topic :: Utilities'
    ]
)
