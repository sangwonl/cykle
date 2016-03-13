# -*- coding: utf-8 -*-
from trello import TrelloApi
from github import Github
from prettytable import PrettyTable
from fabric.api import local
from configparser import ConfigParser
from datetime import timedelta, date, datetime

import sys
import os
import shutil
import getpass
import click
import base64
import webbrowser
import requests
import json
import re


CYKLE_CONFIG_FILE = 'cykle.cfg'


class ContextObj(object):
    def __init__(self):
        self.config = None
        self.trello_api = None
        self.github_api = None


def _get_list_id(ctx, name):
    target_list = None
    lists = ctx.obj.trello_api.boards.get_list(ctx.obj.config.get('trello', 'board_id'))
    for l in lists:
        if l['name'] == name:
            target_list = l
            break
    return target_list


def _auth_params(ctx):
    return dict(key=ctx.obj.config.get('trello', 'apikey'), token=ctx.obj.config.get('trello', 'token'))


def _move_position(ctx, card_id, pos):
    auth = _auth_params(ctx)
    resp = requests.put('https://trello.com/1/cards/%s/pos' % (card_id), params=auth, data=dict(value=pos))
    resp.raise_for_status()


def _assign_to_user(ctx, card_id, user_id):
    auth = _auth_params(ctx)
    resp = requests.post('https://trello.com/1/cards/%s/idMembers' % (card_id), params=auth, data=dict(value=user_id))
    resp.raise_for_status()


@click.group()
@click.pass_context
def cli(ctx):
    ctx.obj.config = ConfigParser()
    ctx.obj.config.read(CYKLE_CONFIG_FILE)
    if len(ctx.obj.config.items()) <= 1:
        return

    ctx.obj.trello_api = TrelloApi(ctx.obj.config.get('trello', 'apikey'), ctx.obj.config.get('trello', 'token'))
    ctx.obj.github_api = Github(ctx.obj.config.get('github', 'username'), base64.b64decode(ctx.obj.config.get('github', 'password')))


@cli.command(name='token')
@click.pass_context
def token(ctx):
    # open token url
    token_url = ctx.obj.trello_api.get_token_url('Cykle', expires='30days', write_access=True)
    webbrowser.open(token_url)

    # get trello token
    trello_token = raw_input('Trello Token: ')

    # save config file
    print ('Updating cykle config file...')
    ctx.obj.config.set('trello', 'token', trello_token)
    with open(CYKLE_CONFIG_FILE, 'w') as cfgfile:
        ctx.obj.config.write(cfgfile)    


@cli.command(name='init')
@click.pass_context
def init(ctx):
    if len(ctx.obj.config.items()) > 1:
        print ('Cykle is already initialized.')
        exit(0)

    # get trello api key
    trello_apikey = raw_input('Trello API Key: ')

    # get trello token
    trello_api = TrelloApi(trello_apikey)
    token_url = trello_api.get_token_url('Cykle', expires='30days', write_access=True)
    webbrowser.open(token_url)
    trello_token = raw_input('Trello Token: ')

    # get trello organization
    trello_orgnization = raw_input('Trello Organization: ')

    # get trello board id
    trello_board_name = raw_input('Trello Board Name: ')
    trello_api = TrelloApi(trello_apikey, trello_token)

    # get all boards of the organization
    # if it is not a member of the organiztion, abort
    try:
        boards = trello_api.organizations.get_board(trello_orgnization)
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            print ('Aborted. You MUST be member of the organization(%s).' % trello_orgnization)
        elif e.response.status_code == 404:
            print ('Aborted. Cannot find the organization(%s), '
                'please refer to the short name of your ORG.' % trello_orgnization)
    finally:
        exit(0)

    # filter the boards by name
    for b in boards:
        if b['name'] == trello_board_name:
            trello_board_id = b['id']

    # get trello list per issue step
    trello_list_backlogs = raw_input('Trello List for BACKLOGS: ')
    trello_list_in_progress = raw_input('Trello List for IN_PROGRESS: ')
    trello_list_code_review = raw_input('Trello List for CODE_REVIEW: ')
    trello_list_closed = raw_input('Trello List for CLOSED: ')

    # github repository info
    github_owner_name = raw_input('Github Owner Name: ')
    github_repo_name = raw_input('Github Repository: ')
    github_username = raw_input('Github Username: ')
    github_password = getpass.getpass('Github Password: ')

    # branch info
    develop_branch = raw_input('Develop Branch: ')

    # generate cykle config file
    print ('Generating cykle config file...')

    ctx.obj.config.add_section('trello')
    ctx.obj.config.set('trello', 'apikey', trello_apikey)
    ctx.obj.config.set('trello', 'token', trello_token)
    ctx.obj.config.set('trello', 'orgnization', trello_orgnization)
    ctx.obj.config.set('trello', 'board_id', trello_board_id)
    ctx.obj.config.set('trello', 'list_in_backlogs', trello_list_backlogs)
    ctx.obj.config.set('trello', 'list_in_progress', trello_list_in_progress)
    ctx.obj.config.set('trello', 'list_code_review', trello_list_code_review)
    ctx.obj.config.set('trello', 'list_closed', trello_list_closed)

    ctx.obj.config.add_section('github')
    ctx.obj.config.set('github', 'owner_name', github_owner_name)
    ctx.obj.config.set('github', 'repo_name', github_repo_name)
    ctx.obj.config.set('github', 'username', github_username)
    ctx.obj.config.set('github', 'password', base64.b64encode(github_password))

    ctx.obj.config.add_section('repository')
    ctx.obj.config.set('repository', 'develop_branch', develop_branch)

    with open(CYKLE_CONFIG_FILE, 'w') as cfgfile:
        ctx.obj.config.write(cfgfile)


@cli.command(name='create')
@click.option('--issuetype', default='issue', help='Create an issue to backlogs')
@click.argument('title')
@click.pass_context
def create(ctx, issuetype, title):
    if issuetype not in ('issue', 'bug'):
        print ('Invalid issue type: %s. (use issue or bug)' % issuetype)
        exit(0)

    backlogs_list = _get_list_id(ctx, ctx.obj.config.get('trello', 'list_in_backlogs'))
    card = ctx.obj.trello_api.cards.new(title, backlogs_list['id'])

    title_with_prefix = '[{0}] {1}'.format(card['idShort'], title)
    ctx.obj.trello_api.cards.update_name(card['id'], title_with_prefix)

    print 'Created the issue: %s' % title_with_prefix


@cli.command(name='issues')
@click.argument('list_name', default='')
@click.pass_context
def issues(ctx, list_name):
    cards = ctx.obj.trello_api.boards.get_card(ctx.obj.config.get('trello', 'board_id'))

    pt = PrettyTable(['card id', 'card name', 'list name', 'members'])
    pt.align['card id'] = 'r'
    pt.align['card name'] = 'l'
    pt.align['list name'] = 'l'

    list_map = {}
    member_map = {}
    for c in cards:
        # list info
        list_id = c['idList']
        the_list = list_map.get(list_id, None)
        if not the_list:
            the_list = ctx.obj.trello_api.lists.get(c['idList'])
            list_map[list_id] = the_list

        if list_name and the_list['name'] != list_name:
            continue

        # member info
        member_names = []
        for mem_id in c['idMembers']:
            member = member_map.get(mem_id, None)
            if not member:
                member = ctx.obj.trello_api.members.get(mem_id)
                member_map[mem_id] = member
            member_names.append(member['fullName'])

        pt.add_row([c['idShort'], c['name'], the_list['name'], ', '.join(member_names)])

    print pt


@cli.command(name='start')
@click.argument('issue_id')
@click.argument('branch_name')
@click.pass_context
def start(ctx, issue_id, branch_name):
    # define develop branch var
    develop_branch = ctx.obj.config.get('repository', 'develop_branch')

    # pull origin before new branch
    local('git checkout {0}'.format(develop_branch))
    local('git pull origin {0}'.format(develop_branch))

    # feature branch from develop branch
    dashed_branch_name = '-'.join(branch_name.lower().split(' '))
    local('git checkout -b issue-{0}-{1} {2}'.format(issue_id, dashed_branch_name, develop_branch))

    # assign issue to starter
    card = ctx.obj.trello_api.boards.get_card_idCard(issue_id, ctx.obj.config.get('trello', 'board_id'))
    user = ctx.obj.trello_api.tokens.get_member(ctx.obj.config.get('trello', 'token'))
    _assign_to_user(ctx, card['id'], user['id'])

    # transition issue to in_progress
    in_progres_list = _get_list_id(ctx, ctx.obj.config.get('trello', 'list_in_progress'))
    ctx.obj.trello_api.cards.update_idList(card['id'], in_progres_list['id'])

    # move to top of the list
    _move_position(ctx, card['id'], 1)


@cli.command(name='pr')
@click.option('--force', default=False)
@click.argument('title', default='')
@click.argument('body', default='')
@click.pass_context
def pr(ctx, force, title, body):
    # get current branch name
    cur_branch_name = local('git rev-parse --abbrev-ref HEAD', capture=True)
    local('git push {0} origin {1}'.format('--force' if force else '', cur_branch_name))

    # create pull request
    repo = ctx.obj.github_api.get_repo('{0}/{1}'.format(
        ctx.obj.config.get('github', 'owner_name'), 
        ctx.obj.config.get('github', 'repo_name'))
    )

    pull_request = repo.create_pull(
        title=title or cur_branch_name,
        body=body,
        base=ctx.obj.config.get('repository', 'develop_branch'),
        head='{0}:{1}'.format(ctx.obj.config.get('github', 'owner_name'), cur_branch_name)
    )

    # extract issue id from branch name
    issue_id = cur_branch_name.split('-')[1]
    card = ctx.obj.trello_api.boards.get_card_idCard(issue_id, ctx.obj.config.get('trello', 'board_id'))

    # comment pull request url on issue
    ctx.obj.trello_api.cards.new_action_comment(card['id'], '{0}'.format(pull_request.html_url))

    # transition to code_review
    code_review_list = _get_list_id(ctx, ctx.obj.config.get('trello', 'list_code_review'))
    ctx.obj.trello_api.cards.update_idList(card['id'], code_review_list['id'])
    _move_position(ctx, card['id'], 'top')


@cli.command(name='close')
@click.argument('issue_id')
@click.argument('delete_remote_branch', default=False)
@click.pass_context
def close(ctx, issue_id, delete_remote_branch):
    # get current branch name
    local('git checkout {0}'.format(ctx.obj.config.get('repository', 'develop_branch')))

    # move develop branch and delete feature branch
    branch_to_delete = local('git branch | grep issue-{0}'.format(issue_id), capture=True)
    local('git branch -D {0}'.format(branch_to_delete))
    if delete_remote_branch:
        local('git push origin --delete {0}'.format(branch_to_delete))

    # extract issue id from branch name
    card = ctx.obj.trello_api.boards.get_card_idCard(issue_id, ctx.obj.config.get('trello', 'board_id'))

    # transition to closed
    closed_list = _get_list_id(ctx, ctx.obj.config.get('trello', 'list_closed'))
    ctx.obj.trello_api.cards.update_idList(card['id'], closed_list['id'])

    # move card to top of the list
    _move_position(ctx, card['id'], 'top')


@cli.command(name='archive')
@click.argument('before_days')
@click.pass_context
def archive(ctx, before_days):
    # verify param: 3d or 3
    if not re.match(r'^\d+(d)?$', before_days):
        print ('Invalid date format')
        exit(0)

    # separate digit
    days = int(re.search(r'\d+', before_days).group(0))
    cutoff_date = timedelta(days=days)
    print ('Now archiving the issues closed before %s day(s) ago.' % cutoff_date.days)

    # get cards on the list_closed
    list_obj = _get_list_id(ctx, ctx.obj.config.get('trello', 'list_closed'))
    cards = ctx.obj.trello_api.lists.get_card(list_obj['id'])

    # filter and archive the issues older than cutoff date
    today = date.today()
    def elapsed_from_closed(card):
        dateLastActivity = card['dateLastActivity'].split('T')[0]
        return today - datetime.strptime(dateLastActivity, '%Y-%m-%d').date()

    cards = filter(lambda card: cutoff_date < elapsed_from_closed(card), cards)
    for c in cards:
        ctx.obj.trello_api.cards.update_closed(c['id'], 'true')

    print ('Totol %d issues archived,' % len(cards))


def main():
    cli(obj=ContextObj())


if __name__ == '__main__':
    main()
