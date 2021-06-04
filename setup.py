from setuptools import find_packages, setup

setup(
    name='src',
    packages=find_packages(),
    version='0.1.0',
    description='Bias correction of air quality CAMS model predictions by using OpenAQ observations.',
    author='Antonio Pérez Velasco / Mario Santa Cruz López',
    license='MIT',
    entrypoints={
        'console_scripts': [
            'extract_cams = src.scripts.extraction_cams:main',
            'extraction_openaq = src.scripts.extraction_openaq:download_openaq_data_from_csv_with_locations_info',
            'transform_data = src.scripts.transformation_data:main'
        ]
    }
)
