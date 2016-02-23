# -*- coding: utf-8 -*-
from trello import TrelloApi
from github import Github
from prettytable import PrettyTable
from fabric.api import local

import sys
import os
import shutil
import getpass
import click
import re
import base64
import webbrowser


def load_cfg_vars_as_dict():
    import cyklecfg
    return {
        'trello_apikey': getattr(cyklecfg, 'TRELLO_APIKEY'),
        'trello_token': getattr(cyklecfg, 'TRELLO_TOKEN'),
        'trello_org': getattr(cyklecfg, 'TRELLO_ORG'),
        'trello_board_id': getattr(cyklecfg, 'TRELLO_BOARD_ID'),
        'github_owner': getattr(cyklecfg, 'GITHUB_OWNER'),
        'github_repo': getattr(cyklecfg, 'GITHUB_REPO'),
        'github_username': getattr(cyklecfg, 'GITHUB_USERNAME'),
        'github_password': getattr(cyklecfg, 'GITHUB_PASSWORD'),
        'develop_branch': getattr(cyklecfg, 'DEVELOP_BRANCH')
    }


@click.group()
@click.pass_context
def cli(ctx):
    try:
        sys.path.append(os.getcwd())
        import cyklecfg
    except ImportError:
        return

    ctx.obj.update(load_cfg_vars_as_dict())
    ctx.obj.update({'trello_api': TrelloApi(ctx.obj['trello_apikey'], ctx.obj['trello_token'])})
    ctx.obj.update({'github_api': Github(ctx.obj['github_username'], base64.b64decode(ctx.obj['github_password']))})


@cli.command(name='init-cykle')
@click.pass_context
def init_cykle(ctx):
    if ctx.obj:
        print 'Cykle is already initialized'
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
    boards = trello_api.organizations.get_board(trello_orgnization)
    for b in boards:
        if b['name'] == trello_board_name:
            trello_board_id = b['id']

    # github repository info
    github_owner_name = raw_input('Github Owner Name: ')
    github_repository = raw_input('Github Repository: ')
    github_username = raw_input('Github Username: ')
    github_password = getpass.getpass('Github Password: ')

    # branch info
    develop_branch = raw_input('Develop Branch: ')

    # generate cykle config file
    print 'generating cykle config file...'
    cfgtext_templ = \
        "TRELLO_APIKEY = '%s'\n" + \
        "TRELLO_TOKEN = '%s'\n" + \
        "TRELLO_ORG = '%s'\n" + \
        "TRELLO_BOARD_ID = '%s'\n" + \
        "GITHUB_OWNER = '%s'\n" + \
        "GITHUB_REPO = '%s'\n" + \
        "GITHUB_USERNAME = '%s'\n" + \
        "GITHUB_PASSWORD = '%s'\n" + \
        "DEVELOP_BRANCH = '%s'\n"    

    cfgtext = cfgtext_templ % (
        trello_apikey,
        trello_token,
        trello_orgnization,
        trello_board_id,
        github_owner_name,
        github_repository,
        github_username,
        base64.b64encode(github_password),
        develop_branch
    )

    cfgfile = open('cyklecfg.py', 'w')
    cfgfile.write(cfgtext)


@cli.command(name='setup-board')
@click.pass_context
def setup_board(ctx):
    lists = ['to_do', 'in_progress', 'code_review', 'to_deploy', 'live_qa', 'closed']
    for l in reversed(lists):
        ctx.obj['trello_api'].lists.new(l, ctx.obj['trello_board_id'])


@cli.command(name='list-card')
@click.argument('list_name', default='')
@click.pass_context
def list_card(ctx, list_name):
    cards = ctx.obj['trello_api'].boards.get_card(ctx.obj['trello_board_id'])

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
            the_list = ctx.obj['trello_api'].lists.get(c['idList'])
            list_map[list_id] = the_list

        if list_name and the_list['name'] != list_name:
            continue

        # member info
        member_names = []
        for mem_id in c['idMembers']:
            member = member_map.get(mem_id, None)
            if not member:
                member = ctx.obj['trello_api'].members.get(mem_id)
                member_map[mem_id] = member
            member_names.append(member['fullName'])

        pt.add_row([c['idShort'], c['name'], the_list['name'], ', '.join(member_names)])

    print pt


def _get_list_id(ctx, name):
    target_list = None
    lists = ctx.obj['trello_api'].boards.get_list(ctx.obj['trello_board_id'])
    for l in lists:
        if l['name'] == name:
            target_list = l
            break
    return target_list


def _move_position(ctx, card_id, pos):
    import requests
    import json

    auth = dict(key=ctx.obj['trello_apikey'], token=ctx.obj['trello_token'])
    resp = requests.put('https://trello.com/1/cards/%s/pos' % (card_id), params=auth, data=dict(value=pos))
    resp.raise_for_status()


@cli.command(name='start')
@click.argument('issue_id')
@click.argument('branch_name')
@click.pass_context
def start(ctx, issue_id, branch_name):
    # feature branch from develop branch
    dashed_branch_name = '-'.join(branch_name.lower().split(' '))
    local('git checkout -b issue-{0}-{1} {2}'.format(issue_id, dashed_branch_name, ctx.obj['develop_branch']))

    # transition issue to in_progress
    in_progres_list = _get_list_id(ctx, 'in_progress')
    card = ctx.obj['trello_api'].boards.get_card_idCard(issue_id, ctx.obj['trello_board_id'])
    ctx.obj['trello_api'].cards.update_idList(card['id'], in_progres_list['id'])
    _move_position(ctx, card['id'], 1)


@cli.command(name='pr')
@click.argument('title', default='')
@click.argument('body', default='')
@click.pass_context
def pr(ctx, title, body):
    # get current branch name
    cur_branch_name = local('git rev-parse --abbrev-ref HEAD', capture=True)
    local('git push origin {0}'.format(cur_branch_name))

    # create pull request
    repo = ctx.obj['github_api'].get_repo('{github_owner}/{github_repo}'.format(**ctx.obj))
    pull_request = repo.create_pull(
        title=title or cur_branch_name,
        body=body,
        base=ctx.obj['develop_branch'],
        head='{0}:{1}'.format(ctx.obj['github_username'], cur_branch_name)
    )

    # extract issue id from branch name
    issue_id = cur_branch_name.split('-')[1]
    card = ctx.obj['trello_api'].boards.get_card_idCard(issue_id, ctx.obj['trello_board_id'])

    # comment pull request url on issue
    ctx.obj['trello_api'].cards.new_action_comment(card['id'], '{0.html_url}'.format(pull_request))

    # transition to code_review
    code_review_list = _get_list_id(ctx, 'code_review')
    ctx.obj['trello_api'].cards.update_idList(card['id'], code_review_list['id'])
    _move_position(ctx, card['id'], 1)


@cli.command(name='finish')
@click.argument('issue_id')
@click.argument('delete_remote_branch', default=False)
@click.pass_context
def finish(ctx, issue_id, delete_remote_branch):
    # get current branch name
    branch_to_delete = local('git rev-parse --abbrev-ref HEAD', capture=True)

    # move develop branch and delete feature branch
    local('git checkout {0}'.format(ctx.obj['develop_branch']))
    local('git branch -D {0}'.format(branch_to_delete))
    if delete_remote_branch:
        local('git push origin --delete {0}'.format(branch_to_delete))

    # extract issue id from branch name
    issue_id = branch_to_delete.split('-')[1]
    card = ctx.obj['trello_api'].boards.get_card_idCard(issue_id, ctx.obj['trello_board_id'])

    # transition to closed
    closed_list = _get_list_id(ctx, 'closed')
    ctx.obj['trello_api'].cards.update_idList(card['id'], closed_list['id'])
    _move_position(ctx, card['id'], 1)


def main():
    cli(obj={})


if __name__ == '__main__':
    main()
