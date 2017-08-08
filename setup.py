from setuptools import setup, find_packages


with open('requirements.txt') as f:
    deps = f.read().splitlines()

setup(name='apidiff',
    version='0.1.0',
    description='CLI tool for diffing responses of HTTP API endpoints',
    url='http://git.develcraft.com/dan/apidiff',
    author='Dan Keder',
    author_email='dan.keder@gmail.com',
    license='MIT',
    packages=find_packages(),
    keywords='jq, json, diff, http, api',
    install_requires=deps,
    include_package_data=True,
    zip_safe=False,
    entry_points={
        'console_scripts': [
            'apidiff=apidiff:main',
        ]
    })
