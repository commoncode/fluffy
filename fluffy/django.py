from __future__ import absolute_import

from fabric.api import env, cd, sudo, runs_once, local, lcd

from .output import notify
from .remote import venv_sudo


def run_manage(command):
    with cd(env.code_dir):
        venv_sudo('./manage.py {0}'.format(command))


def _get_django_version():
    import django
    return django.VERSION


def generate_static_files():
    with lcd(env.web_dir):
        local("rm -rf public/static/*")
        local("grunt --env=dist")
        local("./manage.py collectstatic --noinput")


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
    """ Apply schema migrations based on the Django version used.  """
    notify("Applying database migrations for Django {}".format(
        env.django_version))

    if env.django_version[:3] < (1, 7):
        # Using the command for South migrations
        run_manage('syncdb --noinput > /dev/null')
        run_manage('migrate --ignore-ghost-migrations')
    else:
        # Using the command for Django's migrations (Django 1.7+)
        run_manage('migrate --noinput')
