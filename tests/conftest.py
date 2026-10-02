"""Consistent property-test profiles."""

import os

from hypothesis import settings

settings.register_profile('ci', max_examples=100, derandomize=True, deadline=None)
settings.register_profile('dev', max_examples=30, deadline=None)
settings.load_profile(os.environ.get('HYPOTHESIS_PROFILE', 'dev'))
