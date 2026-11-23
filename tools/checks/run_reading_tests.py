"""Run the isolated Reading Group integration suite from the application folder."""
import unittest

if __name__=='__main__':
    suite=unittest.defaultTestLoader.discover('.',pattern='test_reading_pipeline.py')
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
