#! /usr/bin/env python
# -*- coding: utf-8 -*-

from . import Command as IFace, ResourceExists
from exc import MatchedMultiple
from model import Node, session, Attribute

from logging import getLogger

class Command(IFace):

    __generated = None
    """ flag indicating a value has been generated """

    def generate_value(self):
        """
            The implemetation generates a new password

            However, the method could be more generic and current code live in password attribute
        """
        self.__generated = True
        from subprocess import Popen, PIPE
        pgen = self.conf.get('main','password_generator')
        p = Popen(pgen.split(" "),stdout=PIPE)
        p.wait()
        return p.stdout.read()[:-1]

    def attribute(self):
        """ Creates new attribute """
        a = Attribute()
        a.name = self.args.nodes.pop()

        if self.args.nodes:
            a.descrption = args.nodes.pop()

        session.add(a)
        from sqlalchemy.exc import IntegrityError

        try:
            session.commit()
        except IntegrityError:
            self.die("IntegrityError, attribute name not unique?")

    def get_value(self,attr):
        """
            Returns input from stdin

            For passwords, however, the value is generated by configured generator unless --stdin is given
        """


        getLogger("%s_%s" % (__name__, self.__class__.__name__,)).debug("attr: %s; attr.generator: %s" % (attr, attr.generator))
        if attr and attr.generator:
            if self.args.stdin:
                return self.input()
            
            return self.generate_value()
        return self.input()

    def node(self):
        """ Creates a new node """
        filters = self.tokens_2_filters(self.tokenize_nodes())

        if not filters[-1]['node'] and filters[-1]['attr']:
            new_type = Attribute.get(filters.pop()['attr'])
        else:
            new_type = Attribute.password()

        #if new_type and new_type.one_per_higher_node:
        if new_type:
            filters.append({'attr': new_type})

        
        getLogger("%s_%s" % (__name__, self.__class__.__name__,)).debug("filters: %s" % filters)
        try:
            node = Node.get(filters,create=True)
        except MatchedMultiple as e:
            self.die("Multiple values %s " % (",".join([i.name for i in e.matched]),e.last.name))

        getLogger("%s_%s" % (__name__, self.__class__.__name__,)).debug("node.value: %s" % node.value)

        if node.value and not self.args.force:
            raise ResourceExists()

        # node.attribute.new_value()
        #   could return new value based on the type so it could be more generic
        #   however a new_type would have to not be None

        value = self.get_value(new_type)

        node.value = self.encrypt(value)
        session.commit()

        if self.__generated:
            self.output(value)

    def _run(self,args):
        if args.force and args.stdin:
            from .. import ContradictingArgs
            raise ContradictingArgs("-f --stdin")

        if args.attribute:
            return self.attribute()

        self.node()
