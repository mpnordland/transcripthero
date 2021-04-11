
from helpers import TranscriptHeroTestCase


class UserServiceTestCase(TranscriptHeroTestCase):
    def setUpExtra(self):
        pass

    def test_user_create(self):
        email = "test@rehack.me"
        name = "Chuck Tester"
        password = "password"
        user = self.make_test_user(name, email, password)
        user_id = user.id
        hashed_password = user.password
        self.assertIsNotNone(user_id)
        user = self.user_service.get(user_id)
        self.assertEqual(user.id, user_id)

        self.assertEqual(hashed_password, user.password)
        self.assertEqual(user.email, email)
        self.assertEqual(user.name, name)

    def test_user_roles(self):
        email = "test@rehack.me"
        name = "Chuck Tester"
        password = "password"
        sub_role = self.user_service.find_role("subscriber")
        super_role = self.user_service.find_role("superuser")

        user = self.make_test_user(name, email, password)
        self.assertNotIn(sub_role, user.roles)
        self.assertNotIn(super_role, user.roles)
        self.user_service.add_user_role(user, "superuser")
        self.user_service.add_user_role(user, "subscriber")

        self.assertIn(sub_role, user.roles)
        self.assertIn(super_role, user.roles)

        self.user_service.stop_benefits(user)

        self.assertNotIn(sub_role, user.roles)
        self.assertIn(super_role, user.roles)

        self.user_service.start_benefits(user)

        self.assertIn(sub_role, user.roles)
        self.assertIn(super_role, user.roles)

        self.user_service.remove_user_role(user, super_role)
        self.assertIn(sub_role, user.roles)
        self.assertNotIn(super_role, user.roles)

    def test_get_user(self):
        email = "test@rehack.me"
        name = "Chuck Tester"
        password = "password"

        user = self.make_test_user(name, email, password)
        got_id_user = self.user_service.get(user.id)
        got_email_user = self.user_service.get_by_email(email)

        self.assertEqual(user.id, got_id_user.id)
        self.assertEqual(user.id, got_email_user.id)

        self.assertEqual(email, got_id_user.email)
        self.assertEqual(email, got_email_user.email)

        self.assertEqual(name, got_id_user.name)
        self.assertEqual(name, got_email_user.name)
