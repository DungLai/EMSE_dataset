from methods.regular.regular_api import *
from default.tests.test_utils import testing_setup
from shared.tests.test_utils import common_actions, data_mocking
from base64 import b64encode
from methods.discussions import discussion_detail
from unittest.mock import patch
import flask


class TeseIssueList(testing_setup.DiffgramBaseTestCase):
    """
        
        
        
    """

    def setUp(self):
        # TODO: this test is assuming the 'my-sandbox-project' exists and some object have been previously created.
        # For future tests a mechanism of setting up and tearing down the database should be created.
        super(TeseIssueList, self).setUp()
        project_data = data_mocking.create_project_with_context(
            {
                'users': [
                    {'username': 'Test',
                     'email': 'test@test.com',
                     'password': 'diffgram123',
                     }
                ]
            },
            self.session
        )
        self.project = project_data['project']

    def test_issue_detail_web(self):
        # Create mock tasks
        # Create mock job.
        discussion = data_mocking.create_discussion(
            {
                'project_id': self.project.id,
                'name': 'test',
                'title': 'test',
            },
            self.session,
        )

        job = data_mocking.create_job({
            'name': 'my-test-job',
            'project': self.project
        }, self.session)

        discussion.attach_element(
            session = self.session,
            element = {'type': 'job', 'id': job.id}
        )

        file = data_mocking.create_file({'project_id': job.project.id, 'job_id': job.id}, self.session)

        discussion.attach_element(
            session = self.session,
            element = {'type': 'file', 'id': file.id}
        )

        task = data_mocking.create_task({
            'name': f"task{1}",
            'job': job,
            'file': file,
        }, self.session)

        discussion.attach_element(
            session = self.session,
            element = {'type': 'task', 'id': task.id}
        )
        regular_methods.commit_with_rollback(self.session)

        request_data = {}

        endpoint = f"/api/v1/project/{self.project.project_string_id}/issues/{str(discussion.id)}"
        auth_api = common_actions.create_project_auth(project = job.project, session = self.session)
        credentials = b64encode(f"{auth_api.client_id}:{auth_api.client_secret}".encode()).decode('utf-8')
        response_with_task_id = self.client.get(
            endpoint,
            data = json.dumps(request_data),
            headers = {
                'directory_id': str(job.project.directory_default_id),
                'Authorization': f"Basic {credentials}"
            }
        )
        data = response_with_task_id.json
        self.assertEqual(response_with_task_id.status_code, 200)
        self.assertEqual('attached_elements' in data['issue'], True)
        self.assertEqual(len(data['issue']['attached_elements']), 4)

    def test_issue_detail_core(self):
        discussion = data_mocking.create_discussion(
            {
                'project_id': self.project.id,
                'name': 'test',
                'title': 'test',
            },
            self.session,
        )
        issue_data, log = discussion_detail.discussion_detail_core(
            session = self.session,
            log = regular_log.default(),
            project = self.project,
            discussion_id = discussion.id

        )

        self.assertIsNotNone(issue_data)
        self.assertTrue(len(log['error'].keys()) == 0)
        self.assertEqual(discussion.id, issue_data['id'])
