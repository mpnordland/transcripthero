import unittest

import transcript_hero_web


@unittest.skip
class HomePageTestCase(unittest.TestCase):

    def setUp(self):
        self.app = transcript_hero_web.app.test_client()

    def test_index(self):
        rv = self.app.get('/')
        page_data = rv.data.decode()
        # Check for register button
        self.assertIn('GET STARTED', page_data)
        # Check for login button
        self.assertIn('LOGIN', page_data)

    def test_register(self):
        rv = self.app.get('/register')
        page_data = rv.data.decode()
        self.assertIn("Get Started", page_data)

    def test_login(self):
        rv = self.app.get('/login')
        page_data = rv.data.decode()
        self.assertIn("Welcome", page_data)
        self.assertIn("Forgot your password?", page_data)
        self.assertIn('Login', page_data)
