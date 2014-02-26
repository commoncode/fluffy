from __future__ import absolute_import

from fabric.api import env, cd, sudo, runs_once

from .output import notify
from .remote import venv_sudo


def run_manage(command):
    with cd(env.code_dir):
        venv_sudo('./manage.py {0}'.format(command))


def run_offline_compressor():
    """ Generate minified CSS and JS as well as pre-compile LESS files. """
    notify('Running offline compression')
    run_manage('compress --follow-links > /dev/null')


def collect_static_files():
    notify("Collecting static files")
    with cd(env.code_dir):
        run_manage('collectstatic --noinput > /dev/null')
        sudo('chmod -R g+w public')


@runs_once
def migrate():
    """
    Apply any schema alterations
    """
    notify("Applying database migrations")
    run_manage('syncdb --noinput > /dev/null')
    run_manage('migrate --ignore-ghost-migrations')
