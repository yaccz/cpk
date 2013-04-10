#! /usr/bin/env python
# -*- coding: utf-8 -*-

import os
from copy import deepcopy

from twisted.protocols.basic import LineReceiver
from twisted.internet.error import ConnectionDone

import json

from .xdg import save_data_path
from .utils import Serializable

class Service(Serializable):
    def __init__(self, name, id_as=[], password_as=[]):
        # FIXME: id_as makes sense to be [] but password_as must be non-empty
        # list
        # ∴ FIXME: the order should also be reversed: 1st passwords, then
        # identificators
        """
        :Parameters:
            name : str
                service name
            id_ts : list of str
                service identification attribute names
            password_as : list of str
                password attribute names for this service
        """
        for i in password_as:
            if i in id_as:
                raise ValueError("{0} attribute found in both password and"
                    " identification attributes".format(i))

        self.name, self.id_as, self.password_as = name, id_as, password_as

    def __contains__(self, key):
        return key in self.id_as or key in self.password_as

    def __eq__(self, other):
        return self.name == other.name \
            and self.id_as == other.id_as \
            and self.password_as == other.password_as

class Record(Serializable):
    """
    :ivar service: `Service`
    :ivar attrs: dict
        str -> str
    """
    def __init__(self, service, **attributes):
        """
        :Parameters:
            service : `Service`
        """
        if not isinstance(service, Service):
            raise TypeError("Expected {0} got {1}".
                format(Service, service.__class__))

        self.service = service
        self.attrs = {}
        for name,value in attributes.items():
            self.add_attribute(name, value)

    def add_attribute(self, name, value):
        """
        :Parameters:
            name : str
            value : str
        """
        if not name in self.service:
            raise ValueError("Attribute {0} not in {1}".
                format(name, self.service))

        self.attrs[name] = value

    def to_dict(self):
        d = deepcopy(self.__dict__)
        d['service'] = self.service.name
        # FIXME: the service shenanigans feel wrong.
        # The Record can be serialized just by itself, but to be deserialized
        # it need's extra work as in WalletProtocol.recordReceived
        # also tests.wallet.TestRecord
        return d

    @classmethod
    def from_dict(cls, d):
        return cls(d['service'], **d['attrs'])

    def __eq__(self, other):
        return self.service == other.service \
            and self.attrs == other.attrs

class WalletProtocol(LineReceiver):
    """
    :ivar wallet: `cpk.wallet.Wallet`
    :ivar adapter: `cpk.crypto.Interface`
    :ivar header:
    """
    delimiter = b'\n\n'

    def __init__(self, wallet, adapter):
        self.wallet = wallet
        self.adapter = adapter
        self.read_header = True

    def _get_buffer(self):
        if hasattr(self, '_buffer'):
            # twisted >= 13
            return self._buffer

        return self._LineReceiver__buffer
        # twisted < 13

    def connectionLost(self, reason=ConnectionDone):
        if self._get_buffer():
            raise RuntimeError('Unprocessed data still in the buffer')
    # NOTE: not sure if it is cool to just pass the buffer into lineReceived on
    # connectionLost when reason = ConnectionDone
    # so I'm just gonna require all lines MUST be ended with the delimiter for
    # now

    def lineReceived(self, line):
        line = line.decode('utf-8')
        line = self.adapter.decrypt(line)
        line = json.loads(line)
        if self.read_header:
            self.headerReceived(line)
            self.read_header = False
            return

        self.recordReceived(line)

    def headerReceived(self, header):
        """
        :Parameters:
            header : dict
        """
        if 'services' in header:
            for s in header['services']:
                self.serviceReceived(s)

    def serviceReceived(self, s):
        """
        :Parameters:
            s : dict
        """
        s = Service.from_dict(s)
        self.wallet.add_service(s)

    def recordReceived(self, r):
        """
        :Parameters:
            s : dict
        """
        r['service'] = self.wallet.get_service(r['service_name'])
        del r['service_name']
        r = Record.from_dict(r)
        self.wallet.add_record(r)

class Wallet(object):
    """
    :ivar adapter: `crypto.Interface`
    :ivar services: dict of `Service.name` -> `Service`
    :ivar records: list of `Record`
    """
    def __init__(self, adapter):
        """
        :Parameters:
            adapter : `crypto.Interface`
        """
        self.adapter = adapter
        self.services = {}
        self.records = []

    def _open(self, file_):
        """
        :Parameters:
            file : str
                absolute path to the wallet file
        """
        if not os.path.exists(file_):
            return

        if not os.path.isfile(file_):
            raise RuntimeError('wallet file is not a file {0}'.format(file_))

        wfile = open(file_, 'rb')
        p = WalletProtocol(self, self.adapter)
        p.dataReceived(wfile.read())
        p.connectionLost()

    @staticmethod
    def open(name, crypto_adapter):
        """
        :Parameters:
            name : str
                filename of the wallet file. It is expected in
                $XDG_DATA_HOME/cpk
            crypto_adapter : `cpk.crypto.Interface`
                cryptographic adapter used for actual reading/writing from/to
                wallet file
        :
        """

        w = Wallet(crypto_adapter)
        w._open(os.path.join(save_data_path(),name))
        return w

    def add_service(self, service):
        """
        :Parameters:
            service : `Service`
        """
        if service.name in self.services:
            raise RuntimeError("Duplicit service {0}".format(service.name))

        self.services[service.name] = service

    def get_service(self, service):
        """
        :Parameters:
            service : str
                `Service.name`
        """
        return self.services[service]

    def add_record(self, record):
        self.records.append(record)
