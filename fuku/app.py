import os
import stat

from .module import Module
from .db import get_rc_path
from .utils import entity_already_exists


class App(Module):
    dependencies = ['cluster']

    def __init__(self, **kwargs):
        super().__init__('app', **kwargs)

    def add_arguments(self, parser):
        subp = parser.add_subparsers(help='app help')

        p = subp.add_parser('ls', help='list applications')
        p.set_defaults(app_handler=self.handle_list)

        p = subp.add_parser('mk', help='add an app')
        p.add_argument('name', metavar='NAME', help='app name')
        p.set_defaults(app_handler=self.handle_make)

        # remp = subp.add_parser('remove', help='remove an app')
        # remp.add_argument('name', help='app name')
        # remp.set_defaults(app_handler=self.remove)

        p = subp.add_parser('sl', help='select an app')
        p.add_argument('name', metavar='NAME', help='app name')
        p.set_defaults(app_handler=self.handle_select)

        p = subp.add_parser('run', help='run a command')
        p.add_argument('image', metavar='IMAGE', help='image name')
        p.add_argument('command', metavar='CMD', nargs='+', help='command to run')
        p.set_defaults(app_handler=self.handle_run)

    def handle_list(self, args):
        self.list()

    def list(self):
        for gr in self.iter_groups():
            print(gr.group_name[5:])

    def handle_make(self, args):
        self.make(args.name)

    def make(self, name):
        self.create_group(name)

    def handle_select(self, args):
        self.select(args.name)

    def select(self, name):
        if name and name not in [g.group_name[5:] for g in self.iter_groups()]:
            self.error(f'no app "{name}"')
        self.store_set('selected', name)
        self.clear_parent_selections()

    def handle_run(self, args):
        self.run(args.image, args.command)

    def run(self, img, cmd):
        img = self.client.get_module('image').get_uri(img)
        cmd = ' '.join(cmd or [])
        full_cmd = f'docker run --rm -it {img} {cmd}'
        node_mod = self.client.get_module('node')
        node_mod.mgr_run(full_cmd, tty=True)

    def iter_groups(self):
        iam = self.get_boto_resource('iam')
        for gr in iam.groups.filter(PathPrefix='/fuku/'):
            yield gr

    def create_group(self, name):
        ctx = self.get_context()
        iam = self.get_boto_client('iam')
        with entity_already_exists():
            iam.create_group(
                Path=f'/fuku/{ctx["cluster"]}/{name}/',
                GroupName=f'fuku-{name}'
            )

    def delete_app_group(self, name):
        self.run(
            '$aws iam delete-group'
            ' --group-name fuku-$app',
            {'app': name}
        )

    def get_my_context(self):
        sel = self.store_get('selected')
        if not sel:
            self.error('no app currently selected')
        return {
            'app': sel
        }
