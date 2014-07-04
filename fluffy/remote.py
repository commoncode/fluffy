from __future__ import absolute_import

from StringIO import StringIO
from distutils.version import LooseVersion

from jinja2 import Template

from fabric.operations import put
from fabric.api import env, sudo, cd
from fabric.contrib.files import exists

from .output import notify


def _get_pip_version():
    """ Get version string for remote installed pip (in virtualenv) """
    return venv_sudo("python -c 'import pip; print pip.__version__'")


def venv_sudo(command):
    venv = 'source {0.virtualenv}/bin/activate'.format(env)
    return sudo("{} && {}".format(venv, command))


def delete_old_builds():
    notify('Deleting old builds')
    with cd(env.builds_dir):
        sudo('find . -maxdepth 1 -type d -name "%(build)s*" | sort -r | '
             'sed "1,5d" | xargs rm -rf' % env)


def update_virtualenv(use_wheels=True, update=True, exists_action='w',
                      options=None, insecure_packages=None):
    """
    Install the dependencies in the requirements file
    """
    options = options or ['--download-cache=/root/.pip/cache']

    if use_wheels:
        options.append('--use-wheel')

    if update:
        options.append('-U')

    pip_version = _get_pip_version()

    insecure_packages = insecure_packages or []
    for pkg in insecure_packages:
        options.append('--allow-external {}'.format(pkg))
        if LooseVersion(pip_version) >= LooseVersion('1.5'):
            options.append('--allow-unverified {}'.format(pkg))

    options.append('--exists-action={}'.format(exists_action))

    command = ['pip install'] + options + [
        '-r deploy/requirements/{0.build}.txt'.format(env)]

    with cd(env.code_dir):
        venv_sudo(' '.join(command))


def deploy_cronjobs():
    """
    Deploy the app server cronjobs
    """
    notify('Deploying cronjobs')
    with cd(env.code_dir):
        # Replace variables in cron files
        sudo("rename 's#BUILD#%(build)s#' deploy/cron.d/*" % env)
        sudo("sed -i 's#VIRTUALENV_ROOT#%(virtualenv)s#g' deploy/cron.d/*" % env)
        sudo("sed -i 's#BUILD_ROOT#%(code_dir)s#g' deploy/cron.d/*" % env)
        sudo("sed -i 's#BUILD#%(build)s#g' deploy/cron.d/*" % env)
        sudo("mv deploy/cron.d/* /etc/cron.d" % env)


def restart_supervisord_services():
    services = [env.supervisor_proc]
    if hasattr(env, 'celery_proc') and env.celery_proc:
        services.append(env.celery_proc)
    sudo('supervisorctl restart {}'.format(' '.join(services)))


def switch_symlink():
    notify("Switching symlinks")
    with cd(env.builds_dir):
        # Create new symlink for build folder
        sudo('if [ -h %(build)s ]; then unlink %(build)s; fi' % env)
        sudo('ln -s %(build_dir)s %(build)s' % env)


def upload(local_path, remote_path=None):
    """
    Uploads a file
    """
    if not remote_path:
        remote_path = local_path
    notify("Uploading %s to %s" % (local_path, remote_path))
    put(local_path, remote_path)


def unpack(archive_path):
    """
    Unpacks the tarball into the correct place but doesn't switch
    the symlink
    """
    # Ensure all folders are in place
    sudo('if [ ! -d "{env.builds_dir}" ]; then mkdir -p "{env.builds_dir}";'
         ' fi'.format(env=env))

    notify("Creating remote build folder")
    with cd(env.builds_dir):
        sudo('tar xzf %s' % archive_path)

        # Create new build folder
        sudo('if [ -d "%(build_dir)s" ]; then rm -rf "%(build_dir)s"; fi' % env)
        sudo('mv %(web_dir)s %(build_dir)s' % env)

        # Symlink in uploads folder
        sudo('ln -s ../../../media/%(build)s %(build_dir)s/public/media' % env)

        # Add file indicating Git commit
        sudo('echo -e "refspec: %s\nuser: %s" > %s/build-info' % (env.version, env.user, env.build_dir))

        # Remove archive
        sudo('rm %s' % archive_path)


def deploy_codebase(archive_file, commit_id):
    """
    Push a tarball of the codebase up
    """
    upload(archive_file)
    unpack(archive_file)


def initialise_project():
    """
    Create initial project/build folder structure on remote machine
    """
    if not exists(env.code_dir):
        notify('Setting up remote project structure for %(build)s build' % env)
        sudo('mkdir -p %(project_dir)s' % env)
        with cd(env.project_dir):
            sudo('mkdir -p builds')
            sudo('mkdir -p data/%(build)s' % env)
            sudo('mkdir -p logs/%(build)s' % env)
            sudo('mkdir -p media/%(build)s' % env)
            sudo('mkdir -p run/%(build)s' % env)
            sudo('mkdir -p virtualenvs/%(build)s' % env)

            sudo('`which virtualenv` --no-site-packages %(project_dir)s/virtualenvs/%(build)s/' % env)
            sudo('echo "export DJANGO_CONF=\"conf.%(build)s\"" >> virtualenvs/%(build)s/bin/activate' % env)
        with cd('%(project_dir)s/builds/' % env):
            # Create directory and symlink for "zero" build
            sudo('mkdir %(build)s-0' % env)
            sudo('ln -s %(build)s-0 %(build)s' % env)
        notify('Remote project structure created')
    else:
        notify('Remote directory for {build} build already exists, '
               'skipping'.format(**env))


def upload_template(template_name, remote_path, owner=None, group=None,
                    context= None, **kwargs):
    """
    Render the jinja template *template_name* and upload it to *remote_path*.
    """

    with open(template_name) as fh:
        template = Template(fh.read())

    if context:
        content = template.render(**context)
    else:
        content = template.render(env=env)

    put_kwargs = {'temp_dir': '/tmp', 'mode': '0644'}
    put_kwargs.update(kwargs)
    put(StringIO(content), remote_path, use_sudo=True, **put_kwargs)

    if owner:
        if group:
            owner = "{}:{}".format(owner, group)
        sudo(u'chown {} {}'.format(owner, remote_path))
    else:
        sudo(u'chgrp {} {}'.format(group, remote_path))
