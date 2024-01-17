import os
import setuptools

def package_data(pkg, roots):
    """Generic function to find package_data.

    All of the files under each of the `roots` will be declared as package
    data for package `pkg`.

    """
    data = []
    for root in roots:
        for dirname, _, files in os.walk(os.path.join(pkg, root)):
            for fname in files:
                data.append(os.path.relpath(os.path.join(dirname, fname), pkg))

    return {pkg: data}

setuptools.setup(
    name="eol_survey",
    version="0.0.1",
    author="matias melo",
    author_email="matias.melo@uchile.cl",
    description="Eol Survey ",
    long_description="Eol Survey ",
    url="https://eol.uchile.cl",
    packages=setuptools.find_packages(),
    package_data=package_data("eol_survey", ["static", "public"]),
    classifiers=[
        "Programming Language :: Python :: 2",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=[
        'XBlock',
    ],
    entry_points={
        "lms.djangoapp": [
            "eol_survey = eol_survey.apps:EolSurveyConfig",
        ],       
        "cms.djangoapp": [
            "eol_survey = eol_survey.apps:EolSurveyConfig",
        ],          
        'xblock.v1': [
            'eol_survey = eol_survey:EolSurveyConsumerXBlock',
        ]
    },
)
