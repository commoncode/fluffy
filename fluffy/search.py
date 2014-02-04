from __future__ import absolute_import

from fabric.api import env, sudo, cd

from .output import notify
from .remote import venv_sudo


def deploy_solr():
    """
    Create new schema.xml for Solr through haystack and restart solr.
    """
    notify('Update SOLR indexes')
    with cd(env.code_dir):
        sudo("cp -rf deploy/solr/* %(solr_dir)s/conf" % env)
        sudo('service tomcat6 restart')
        venv_sudo('source %s/bin/activate && ./manage.py rebuild_index')
