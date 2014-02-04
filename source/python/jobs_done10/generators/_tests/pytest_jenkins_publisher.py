from ben10.filesystem import GetFileContents, ListFiles
from jobs_done10.generators.jenkins import JenkinsJob, JenkinsJobPublisher



#===================================================================================================
# Test
#===================================================================================================
class Test(object):

    def testPublishToDirectory(self, embed_data):
        self._GetPublisher().PublishToDirectory(embed_data['.'])

        assert set(ListFiles(embed_data['.'])) == set([
            'space-milky_way-jupiter', 'space-milky_way-mercury', 'space-milky_way-venus'])

        assert GetFileContents(embed_data['space-milky_way-jupiter']) == 'jupiter'
        assert GetFileContents(embed_data['space-milky_way-mercury']) == 'mercury'
        assert GetFileContents(embed_data['space-milky_way-venus']) == 'venus'


    def testPublishToUrl(self, monkeypatch):
        mock_jenkins = self._MockJenkinsAPI(monkeypatch)

        new_jobs, updated_jobs, deleted_jobs = self._GetPublisher().PublishToUrl(
            url='jenkins_url',
            username='jenkins_user',
            password='jenkins_pass',
        )
        assert set(new_jobs) == mock_jenkins.NEW_JOBS == set(['space-milky_way-venus', 'space-milky_way-jupiter'])
        assert set(updated_jobs) == mock_jenkins.UPDATED_JOBS == set(['space-milky_way-mercury'])
        assert set(deleted_jobs) == mock_jenkins.DELETED_JOBS == set(['space-milky_way-saturn'])


    def testPublishToUrl2(self, monkeypatch):
        mock_jenkins = self._MockJenkinsAPI(monkeypatch)

        publisher = self._GetPublisher()
        publisher.jobs = {}

        new_jobs, updated_jobs, deleted_jobs = publisher.PublishToUrl(
            url='jenkins_url',
            username='jenkins_user',
            password='jenkins_pass',
        )
        assert set(new_jobs) == mock_jenkins.NEW_JOBS == set()
        assert set(updated_jobs) == mock_jenkins.UPDATED_JOBS == set()
        assert set(deleted_jobs) == mock_jenkins.DELETED_JOBS == set(['space-milky_way-mercury', 'space-milky_way-saturn'])


    def _GetPublisher(self):
        job_group = 'space-milky_way'
        jobs = [
            JenkinsJob(name='space-milky_way-jupiter', xml='jupiter'),
            JenkinsJob(name='space-milky_way-mercury', xml='mercury'),
            JenkinsJob(name='space-milky_way-venus', xml='venus'),
        ]

        return JenkinsJobPublisher(job_group, jobs)


    def _MockJenkinsAPI(self, monkeypatch):
        class MockJenkins(object):
            NEW_JOBS = set()
            UPDATED_JOBS = set()
            DELETED_JOBS = set()

            def __init__(self, url, username, password):
                assert url == 'jenkins_url'
                assert username == 'jenkins_user'
                assert password == 'jenkins_pass'

            def get_jobs(self):
                return [
                    {'name' : u'space-milky_way-mercury'},
                    {'name' : u'space-milky_way-saturn'},
                ]

            def create_job(self, name, xml):
                self.NEW_JOBS.add(name)

            def reconfig_job(self, name, xml):
                self.UPDATED_JOBS.add(name)

            def delete_job(self, name):
                self.DELETED_JOBS.add(name)


        import jenkins
        monkeypatch.setattr(jenkins, 'Jenkins', MockJenkins)

        return MockJenkins
