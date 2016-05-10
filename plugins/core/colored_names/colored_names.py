import re

from datetime import datetime

from base_plugin import BasePlugin
from packets.packet_types import chat_received, Packets
from utility_functions import build_packet


class ColoredNames(BasePlugin):
    """
    Plugin that brings colors to player names in the chat box.
    """
    name = 'colored_names'
    depends = ['player_manager_plugin']

    def activate(self):
        super(ColoredNames, self).activate()
        self.player_manager = self.plugins[
            'player_manager_plugin'
        ].player_manager

    def on_chat_received(self, data):
        now = datetime.now()
        try:
            p = chat_received().parse(data.data)
            if p.name == 'server':
                return
            # Running a regex substitution on every chat message isn't exactly great but it'll have to do for now.
            sender = self.player_manager.get_by_name(
              str(
                re.sub('(\\^\\w+;|\\^#\\w+;|\\W)|(\\s\\s+)', '', p.name)
              )
            )
            if self.config.chattimestamps:
                p.name = '{}> <{}'.format(
                    now.strftime('%H:%M'),
                    sender.colored_name(self.config.colors)
                )
            else:
                p.name = sender.colored_name(self.config.colors)
            self.protocol.transport.write(
                build_packet(Packets.CHAT_RECEIVED, chat_received().build(p))
            )
        except AttributeError as e:
            self.logger.warning(
                'Received AttributeError in colored_name. %s', str(e)
            )
            self.protocol.transport.write(data.original_data)
        return False
