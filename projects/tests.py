from django.test import TestCase, Client
from django.urls import reverse
from django.core import mail
from django.core.exceptions import ValidationError
from .models import Team, TeamMember, User


class TeamManagementTests(TestCase):
    def setUp(self):
        # Create test users
        self.owner = User.objects.create_user('owner', 'owner@test.com', 'password')
        self.member = User.objects.create_user('member', 'member@test.com', 'password')
        self.client = Client()

        # Create test team
        self.team = Team.objects.create(
            name='Test Team',
            description='Test Description',
            owner=self.owner
        )

        # Create owner's team membership
        TeamMember.objects.create(
            team=self.team,
            user=self.owner,
            role='owner',
            created_by=self.owner
        )

    def test_team_creation(self):
        self.client.login(username='owner', password='password')
        response = self.client.post(reverse('team_create'), {
            'name': 'New Team',
            'description': 'New Description'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Team.objects.filter(name='New Team').exists())

    def test_add_member(self):
        self.client.login(username='owner', password='password')
        response = self.client.post(
            reverse('add_team_member', kwargs={'team_id': self.team.id}),
            {
                'email': self.member.email,
                'role': 'member'
            }
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            TeamMember.objects.filter(team=self.team, user=self.member).exists()
        )

    def test_remove_member(self):
        # Add member first
        member = TeamMember.objects.create(
            team=self.team,
            user=self.member,
            role='member',
            created_by=self.owner
        )

        self.client.login(username='owner', password='password')
        response = self.client.post(
            reverse('remove_team_member', kwargs={
                'team_id': self.team.id,
                'member_id': member.id
            }),
            {
                'notify_member': True
            }
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            TeamMember.objects.filter(team=self.team, user=self.member).exists()
        )
        self.assertEqual(len(mail.outbox), 1)

    def test_update_member_role(self):
        member = TeamMember.objects.create(
            team=self.team,
            user=self.member,
            role='member',
            created_by=self.owner
        )

        self.client.login(username='owner', password='password')
        response = self.client.post(
            reverse('update_member_role', kwargs={
                'team_id': self.team.id,
                'member_id': member.id
            }),
            {
                'role': 'manager'
            }
        )
        self.assertEqual(response.status_code, 200)
        member.refresh_from_db()
        self.assertEqual(member.role, 'manager')


class TeamIntegrationTests(TestCase):
    def test_full_team_workflow(self):
        # Create users
        owner = User.objects.create_user('owner', 'owner@test.com', 'password')
        member = User.objects.create_user('member', 'member@test.com', 'password')

        # Login
        self.client.login(username='owner', password='password')

        # Create team
        response = self.client.post(reverse('team_create'), {
            'name': 'Integration Team',
            'description': 'Testing full workflow'
        })
        team = Team.objects.get(name='Integration Team')

        # Add member
        response = self.client.post(
            reverse('add_team_member', kwargs={'team_id': team.id}),
            {'email': member.email, 'role': 'member'}
        )

        # Update member role
        member_obj = TeamMember.objects.get(team=team, user=member)
        response = self.client.post(
            reverse('update_member_role', kwargs={
                'team_id': team.id,
                'member_id': member_obj.id  # Add the member_id parameter
            }),
            {'role': 'manager'}  # Only send role in POST data
        )

        # Remove member
        response = self.client.post(
            reverse('remove_team_member', kwargs={
                'team_id': team.id,
                'member_id': member_obj.id  # Add the member_id parameter
            }),
            {'notify_member': True}
        )

        # Verify final state
        self.assertEqual(team.members.count(), 1)  # Only owner remains