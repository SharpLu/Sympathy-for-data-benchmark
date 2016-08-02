# Copyright (c) 2013, System Engineering Software Society
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the System Engineering Software Society nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.
# IN NO EVENT SHALL SYSTEM ENGINEERING SOFTWARE SOCIETY BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
from .. types import types
from .. types import factory


class Ports(object):
    def __init__(self, ports):
        self.ports = ports
        self._lookup = {port['name']: port
                        for port in self.ports if 'name' in port}

    def __getitem__(self, key):
        try:
            return self.ports[key]
        except TypeError:
            return self._lookup[key]

    def __iter__(self):
        for item in self.ports:
            yield item

    def __unicode__(self):
        return u'\n'.join(unicode(item) for item in self)

    def __str__(self):
        return unicode(self).encode('utf-8')


class PortType(object):
    """Port is the interface for ports."""

    required_fields = ['description', 'type', 'scheme']
    optional_fields = ['name', 'requiresdata']

    def __init__(self, description, port_type, scheme, **kwargs):
        self.description = description
        self.type = port_type
        self.scheme = scheme

        for key, value in kwargs.items():
            if key in self.optional_fields:
                setattr(self, key, value)

    def to_dict(self):
        """
        Return dict contaning the required fields:
            'description',
            'type',
            'scheme'.
        Optionally:
            'name'.
            'requiresdata'

        The values should all be of string type.
        """
        result = {}
        for key in self.required_fields + self.optional_fields:
            try:
                attr = getattr(self, key)
                if attr is not None:
                    result[key] = attr
            except:
                pass
        return result

    @staticmethod
    def from_dict(data):
        required = []
        required = [data[key] for key in PortType.required_fields]
        optional = {}
        for key in PortType.optional_fields:
            if key in data:
                optional[key] = data[key]

        return PortType(*required, **optional)

    def __contains__(self, key):
        return (key in self.required_fields or
                key in self.optional_fields and hasattr(self, key))

    def __getitem__(self, key):
        if key in self:
            return getattr(self, key)

    def __unicode__(self):
        return u'**{}** : {}\n    {}'.format(getattr(self, 'name', ''),
                                             self.type,
                                             self.description)

    def __str__(self):
        return unicode(self).encode('utf-8')


def CustomPort(port_type, description, name=None):
    return PortType(description, port_type, 'hdf5', name=name,
                    requiresdata=None)


class Port(object):
    """Provides staticmethods to create Ports for built in types."""

    @staticmethod
    def Table(description, name=None, **kwargs):
        return CustomPort('table', description, name)

    @staticmethod
    def Tables(description, name=None, **kwargs):
        return CustomPort('[table]', description, name)

    @staticmethod
    def TableDict(description, name=None, **kwargs):
        return CustomPort('{table}', description, name)

    @staticmethod
    def ADAF(description, name=None, **kwargs):
        return CustomPort('adaf', description, name)

    @staticmethod
    def ADAFs(description, name=None, **kwargs):
        return CustomPort('[adaf]', description, name)

    # Keep old names for backwards compatibility
    Adaf = ADAF
    Adafs = ADAFs

    @staticmethod
    def Figure(description, scheme=None, name=None, **kwargs):
        return PortType(description, 'figure', 'text', name=name, **kwargs)

    @staticmethod
    def Figures(description, scheme=None, name=None, **kwargs):
        return PortType(description, '[figure]', 'text', name=name, **kwargs)

    @staticmethod
    def Datasource(description, scheme=None, name=None, **kwargs):
        return PortType(description, 'datasource', 'text', name=name,
                        **kwargs)

    @staticmethod
    def Datasources(description, scheme=None, name=None, **kwargs):
        return PortType(description, '[datasource]', 'text', name=name,
                        **kwargs)

    @staticmethod
    def Text(description, name=None, **kwargs):
        return CustomPort('text', description, name)

    @staticmethod
    def Texts(description, name=None, **kwargs):
        return CustomPort('[text]', description, name)

    @staticmethod
    def Custom(port_type, description, name=None, scheme='hdf5'):
        return PortType(description, port_type, scheme, name=name)


class RunPorts(object):
    """
    Provides ways to access Ports.

    In addition to accessing by string key it is also possible to access using
    numeric indices.

    Ports with names can be accessed using getattr.
    """
    def __init__(self, ports, infos):
        self.__ports = ports
        self.__infos = infos
        self.__lookup = {info['name']: port
                         for port, info in zip(ports, infos) if 'name' in info}

    def __getitem__(self, key):
        try:
            result = self.nth(key)
        except (IndexError, TypeError):
            result = self.__lookup[key]
        except KeyError:
            raise KeyError('No port named: "{}"'.format(key))
        return result

    def __iter__(self):
        return iter(self.__ports)

    def __contains__(self, key):
        return str(key) in self.__lookup

    def __len__(self):
        return len(self.__ports)

    def __unicode__(self):
        return '\n'.join(unicode(PortType.from_dict(info))
                         for info in self.__infos)

    def __str__(self):
        return unicode(self).encode('utf-8')

    @property
    def first(self):
        return self.nth(0)

    @property
    def second(self):
        return self.nth(1)

    @property
    def third(self):
        return self.nth(2)

    @property
    def fourth(self):
        return self.nth(3)

    @property
    def fifth(self):
        return self.nth(4)

    def nth(self, n):
        return self.__ports[n]


_use_linking = True


def disable_linking():
    """
    Internal function for disabling linking.
    Do not use this in function in client code.

    It globally disables linking, currently used to avoid a known bug in h5py
    related to h5py.ExternalLink:s and open files.
    """
    global _use_linking
    _use_linking = False


def port_generator(port_information, mode, link, expanded=False,
                   managed=False, no_datasource=False):
    """
    Return generator for port.
    Typaliases should be simplified with intra-dependencies expanded.
    """
    link = link and _use_linking
    alias = port_information['type']

    if no_datasource:
        return factory.typefactory.from_type(types.from_string(alias))
    else:
        return port_type_generator(
            port_information,
            types.from_string(alias),
            mode,
            link,
            managed)


def port_type_generator(port_information, type_expanded, mode, link,
                        managed=False):
    """Return generator for port."""
    link = link and _use_linking
    uri = (
        u'{scheme}://{resource}#type={type}&path=/&mode={mode}&link={link}')
    filled_uri = uri.format(scheme=port_information['scheme'],
                            resource=port_information['file'],
                            type=type_expanded,
                            mode=mode,
                            link=link)
    return factory.typefactory.from_url(filled_uri,
                                        managed=managed)


def typealiases_parser(typealiases):
    """Parse and return dictionary of typaliases."""
    return {alias:
            types.from_string_alias(
                'sytypealias {0} = {1}'.format(alias, value['type']))
            for alias, value in typealiases.items()}


def typealiases_expander(typealiases_parsed):
    """
    Return dictionary of typealiases.
    The intra-dependencies are expanded.
    """
    return dict(
        types.simplify_aliases(typealiases_parsed.values()))
