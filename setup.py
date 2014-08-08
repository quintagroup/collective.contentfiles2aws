from setuptools import setup, find_packages
import os

version = '1.3.1'

setup(name='collective.contentfiles2aws',
      version=version,
      description="Allows to store files and images on amazon s3 service.",
      long_description=open("README.txt").read() + "\n" +
                       open(os.path.join("docs", "HISTORY.txt")).read(),
      classifiers=[
        "Programming Language :: Python",
        ],
      keywords='Plone AWS',
      author='Taras Melnychuk',
      author_email='melnychuktaras@gmail.com',
      url='https://github.com/martinschoel/collective.contentfiles2aws.git',
      license='GPL',
      packages=find_packages(exclude=['ez_setup']),
      namespace_packages=['collective'],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'setuptools',
          'boto',
      ],
      extras_require = {'tests': ['plone.app.testing',]},
      entry_points="""
      # -*- Entry points: -*-
      [z3c.autoinclude.plugin]
      target = plone
      """,
      )
