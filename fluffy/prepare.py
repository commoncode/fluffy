from __future__ import absolute_import

import os
import datetime

from fabric.colors import red
from fabric.operations import prompt
from fabric.api import env, local, runs_once

from .output import notify


def set_ssh_user():
    env.user = os.getenv('TANGENT_USER')
    if not env.user:
        env.user = prompt(
            red('Username for remote host? [default is current user] '))

    if not env.user:
        env.user = os.getenv('USER')


@runs_once
def set_reference_to_deploy_from(branch):
    """
    Determine the refspec (tag or commit ID) to build from

    The role of this task is simply to set the env.version variable
    which is used later on.
    """
    notify("Determine the git reference to deploy from")
    # Versioning - we either deploy from a tag or we create a new one
    local('git fetch --tags')

    if env.build == 'test':
        # Allow a new tag to be set, or generate on automatically
        print ''
        create_tag = prompt(red('Tag this release? [y/N] '))
        if create_tag.lower() == 'y':
            notify("Showing latest tags for reference")
            local('git tag | sort -V | tail -5')
            env.version = prompt(red('Tag name [in format x.x.x]? '))
            notify("Tagging version %s" % env.version)
            local('git tag %s -m "Tagging version %s in fabfile"' % (env.version, env.version))
            local('git push --tags')
        else:
            deploy_version = prompt(red('Build from a specific commit (useful for debugging)? [y/N] '))
            print ''
            if deploy_version.lower() == 'y':
                env.version = prompt(red('Choose commit to build from: '))
            else:
                env.version = local('git rev-parse %s' % branch, capture=True).strip()
    else:
        # An existing tag must be specified to deploy to QE or PE
        local('git tag | sort -V | tail -5')
        env.version = prompt(red('Choose tag to build from: '))
        # Check this is valid
        notify("Checking chosen tag exists")
        local('git tag | grep "%s"' % env.version)

    if env.build == 'prod':
        # If a production build, then we ensure that the master branch
        # gets updated to include all work up to this tag
        notify("Merging tag into master")
        local('git checkout master')
        local('git merge %s' % env.version)
        local('git push origin master')
        local('git checkout develop')


def select_deployment(repo='origin'):
    # Ensure we have latest code locally
    branch = local('git branch | grep "^*" | cut -d" " -f2', capture=True)
    update_codebase(branch, repo)
    set_reference_to_deploy_from(branch)

    notify("Checking out the specified tag")
    local("git checkout {}".format(env.version))


def prepare(repo='origin', include_dirs=None):
    notify('BUILDING TO %s' % env.build.upper())

    include_dirs = include_dirs or []

    # Create a build file ready to be pushed to the servers
    notify("Building from refspec %s" % env.version)

    tar_file = '/tmp/build-{}.tar'.format(str(env.version).replace('/', '-'))
    env.build_file = '{}.gz'.format(tar_file)

    local('git archive --format tar {} {} -o {}'.format(
        env.version, env.web_dir, tar_file))

    if include_dirs:
        local('tar rf {tar} {dirs}'.format(
            dirs=' '.join(include_dirs), tar=tar_file))

    local('gzip {} > {}'.format(tar_file, env.build_file))

    # Set timestamp now so it is the same on all servers after deployment
    now = datetime.datetime.now()
    env.build_dir = '%s-%s' % (env.build, now.strftime('%Y-%m-%d-%H-%M'))
    env.code_dir = '%s/%s' % (env.builds_dir, env.build_dir)


@runs_once
def update_codebase(branch, repo):
    """
    Update codebase from the Git repo
    """
    notify(
        'Updating codebase from remote "{}", branch "{}"'.format(repo, branch))
    local('git pull {} {}'.format(repo, branch))
    notify('Push any local changes to remote {}'.format(branch))
    local('git push {} {}'.format(repo, branch))
