from base_plugin import SimpleCommandPlugin
from plugins.core.player_manager_plugin import UserLevels, permissions
from utility_functions import extract_name


class ClaimsPlugin(SimpleCommandPlugin):
    """
    Allows planets to be either protector or unprotected. On protected planets,
    only admins can build. Planets are unprotected by default.
    """
    name = 'claims'
    description = 'Claims planets.'
    commands = ['claim', 'unclaim', 'claim_list', 'unclaimable', 'claim_add', 'claim_remove']
    depends = ['player_manager_plugin', 'command_plugin', 'planet_protect']

    def activate(self):
        super(ClaimsPlugin, self).activate()
        try:
            self.max_claims = self.config.plugin_config['max_claims']
        except KeyError:
            self.max_claims = 5
        self.unclaimable_planets = self.config.plugin_config.get(
            'unclaimable_planets', []
        )
        self.protected_planets = self.config.config['plugin_config'][
            'planet_protect']['protected_planets']
        self.player_planets = self.config.config['plugin_config'][
            'planet_protect']['player_planets']
        self.player_manager = self.plugins[
            'player_manager_plugin'
        ].player_manager

    @permissions(UserLevels.ADMIN)
    def unclaimable(self, data):
        """
        Set the current planet as unclaimable.
        Syntax: /unclaimable
        """
        planet = self.protocol.player.planet
        on_ship = self.protocol.player.on_ship
        if on_ship:
            self.protocol.send_chat_message(
                '^green;Can\'t claim ships (at the moment)'
            )
            return
        if planet not in self.unclaimable_planets:
            self.unclaimable_planets.append(planet)
            self.protocol.send_chat_message(
                '^green;Planet successfully set as unclaimable.'
            )
            self.logger.info('Planet %s set as unclaimable', planet)
        else:
            self.unclaimable_planets.remove(planet)
            self.protocol.send_chat_message(
                '^green;Planet successfully removed from unclaimable list.'
            )
            self.logger.info('Planet %s removed as unclaimable', planet)
        self.save()

    @permissions(UserLevels.GUEST)
    def claim(self, data):
        """
        Claims the current planet. Only administrators and allowed players can
        build on claimed planets.\nSyntax: /claim [player]
        """
        if self.protocol.player.planet in self.unclaimable_planets:
            self.protocol.send_chat_message(
                '^green;This planet ^red;cannot^green; be claimed!'
            )
            return
        try:
            my_storage = self.protocol.player.storage
        except AttributeError:
            return

        # set storage to 0 if player never used any of the claim commands
        if 'claims' not in my_storage:
            my_storage['claims'] = 0
            self.protocol.player.storage = my_storage

        # check if max claim limit has been reached
        if int(my_storage['claims']) >= self.max_claims:
            my_storage['claims'] = self.max_claims
            self.protocol.player.storage = my_storage
            self.protocol.send_chat_message(
                '^green;You already have max (^red;%s^green;) '
                'claimed planets!'.format(self.max_claims)
            )

        # assuming player is eligible to claim
        elif 0 <= int(my_storage['claims']) <= self.max_claims:
            planet = self.protocol.player.planet
            on_ship = self.protocol.player.on_ship
            if not data:
                addplayer = self.protocol.player.org_name
                first_name_color = self.protocol.player.colored_name(
                    self.config.colors
                )
            else:
                addplayer = data[0]
                try:
                    addplayer, rest = extract_name(data)
                    addplayer = self.player_manager.get_by_name(
                        addplayer
                    ).org_name
                    first_name_color = self.player_manager.get_by_org_name(
                        addplayer
                    ).colored_name(self.config.colors)
                except:
                    self.protocol.send_chat_message(
                        '^green;There\'s no player named: ^yellow;{}'.format(
                            addplayer
                        )
                    )
                    return

            first_name = str(addplayer)
            orgplayer = self.protocol.player.org_name

            try:
                count = 1
                for name in self.player_planets[planet]:
                    if name != str(orgplayer) and count == 1:
                        self.protocol.send_chat_message(
                            '^green;You can only claim free planets!'
                        )
                        return
                    count += 1
            except:
                if first_name != orgplayer:
                    self.protocol.send_chat_message(
                        '^green;Use only /claim if you wish to claim a planet!'
                    )
                    return

            try:
                for _ in self.player_planets:
                    if first_name in self.player_planets[
                        self.protocol.player.planet
                    ]:
                        self.protocol.send_chat_message(
                            '^green;Player ^yellow;{}^green; is already in '
                            'planet protect list.' .format(first_name_color)
                        )
                        return
            except:
                pass

            # reset planet back to current planet
            planet = self.protocol.player.planet
            if on_ship and not ('force' in ' '.join(data).lower()):
                self.protocol.send_chat_message(
                    '^green;Can\'t claim ships (at the moment)'
                )
                return
            if planet == 'On Outpost':
                self.protocol.send_chat_message('^green;Instances ^red;cannot^green; be claimed.')
                self.logger.info('Claiming of an instance denied.')
                return
            if planet not in self.protected_planets:
                self.protected_planets.append(planet)
                self.protocol.send_chat_message('^green;Planet successfully claimed.')
                self.logger.info('Protected planet %s', planet)
                my_storage['claims'] = int(my_storage['claims']) + 1
                self.protocol.player.storage = my_storage
                if first_name:
                    if planet not in self.player_planets:
                        self.player_planets[planet] = [first_name]
                    else:
                        self.player_planets[planet] = (
                            self.player_planets[planet] + [first_name]
                        )
                    self.protocol.send_chat_message(
                        '^green;Adding ^yellow;{}^green; to planet list'.format(
                            first_name_color
                        )
                    )
            else:
                if first_name:
                    self.protocol.send_chat_message(
                        '^green;Planet is already claimed!'
                    )
                else:
                    if planet not in self.player_planets:
                        self.player_planets[planet] = [first_name]
                    else:
                        self.player_planets[planet] = (
                            self.player_planets[planet] + [first_name]
                        )
                    self.protocol.send_chat_message(
                        '^green;Adding ^yellow;%s^green; to planet list'.format(
                            first_name_color
                        )
                    )

        self.save()

    @permissions(UserLevels.GUEST)
    def claim_list(self, data):
        """
        Displays players registered to the protected planet.
        Syntax: /claim_list
        """
        try:
            my_storage = self.protocol.player.storage
        except AttributeError:
            return

        if 'claims' not in my_storage:
            my_storage['claims'] = 0
            self.protocol.player.storage = my_storage

        planet = self.protocol.player.planet
        on_ship = self.protocol.player.on_ship
        if on_ship:
            self.protocol.send_chat_message(
                '^green;Can\'t claim ships (at the moment)'
            )
            return
        if planet in self.player_planets:
            self.protocol.send_chat_message(
                '^green;Claimed ^cyan;{}^green; of max ^red;{}^green; '
                'claimed planets.'.format(
                    my_storage['claims'], self.max_claims
                )
            )
            self.protocol.send_chat_message(
                '^green;Players registered to this planet: ^yellow;{}'.format(
                    '^green;, ^yellow;'.join(self.player_planets[planet])
                    .replace('[', '')
                    .replace(']', '')
                )
            )
        elif planet in self.unclaimable_planets:
            self.protocol.send_chat_message(
                '^green;Claimed ^cyan;{}^green; of max ^red;{}^green; '
                'claimed planets.'.format(
                    my_storage['claims'],
                    self.max_claims
                )
            )
            self.protocol.send_chat_message(
                '^green;This planet ^red;cannot^green; be claimed!'
            )
        else:
            self.protocol.send_chat_message(
                '^green;Claimed ^cyan;%s^green; of max ^red;%s^green; '
                'claimed planets.'.format(
                    my_storage['claims'], self.max_claims
                )
            )
            self.protocol.send_chat_message('Planet has not been claimed!')

    @permissions(UserLevels.GUEST)
    def unclaim(self, data):
        """
        Removes claimed planet, or removes a registered player.
        Syntax: /unclaim [player]
        """
        try:
            my_storage = self.protocol.player.storage
        except AttributeError:
            return
        if int(my_storage.get('claims', 0)) <= 0:
            my_storage['claims'] = 0
            self.protocol.player.storage = my_storage
            self.protocol.send_chat_message('^green;You have no claimed planets!')
        else:
            planet = self.protocol.player.planet
            on_ship = self.protocol.player.on_ship
            if not data:
                addplayer = self.protocol.player.org_name
                first_name_color = self.protocol.player.colored_name(
                    self.config.colors
                )
            else:
                addplayer, rest = extract_name(data)
                first_name_color = addplayer

            first_name = str(addplayer)
            orgplayer = self.protocol.player.org_name

            if on_ship:
                self.protocol.send_chat_message(
                    '^green;Can\'t claim ships (at the moment)'
                )
                return
            try:
                count = 1
                for name in self.player_planets[planet]:
                    if name != str(orgplayer) and count == 1:
                        self.protocol.send_chat_message(
                            '^green;You can only unclaim planets you\'ve claimed!'
                        )
                        return
                    if data and first_name == str(orgplayer):
                        self.protocol.send_chat_message(
                            '^green;Use only /unclaim if you wish to '
                            'remove protection!'
                        )
                        return
                    count += 1
            except:
                pass
            if not data:
                if planet in self.protected_planets:
                    del self.player_planets[planet]
                    self.protected_planets.remove(planet)
                    self.protocol.send_chat_message(
                        '^green;Planet successfully unclaimed.'
                    )
                    self.logger.info('Unprotected planet %s', planet)
                    my_storage['claims'] = int(my_storage['claims']) - 1
                    self.protocol.player.storage = my_storage
                else:
                    self.protocol.send_chat_message(
                        '^green;Planet has not been claimed!'
                    )
            else:
                if first_name in self.player_planets[planet]:
                    self.player_planets[planet].remove(first_name)
                    self.protocol.send_chat_message(
                        '^green;Removed ^yellow;{}^green; from planet list'.format(
                            first_name_color
                        )
                    )
                else:
                    self.protocol.send_chat_message(
                        '^green;Cannot remove ^yellow;{}^green; '
                        'from planet list (not in list)'.format(
                            first_name_color
                        )
                    )
        self.save()

    @permissions(UserLevels.GUEST)
    def claim_add(self, data):
        """
        Adds a player to a planet's claim list. Only the owner of the planet or an admin can use this.
        Syntax: /claim_add <player>
        """
        if self.protocol.player.planet in self.unclaimable_planets:
            self.protocol.send_chat_message(
                '^green;This planet ^red;cannot^green; be claimed!'
            )
            return
        try:
            my_storage = self.protocol.player.storage
        except AttributeError:
            return

        # set storage to 0 if player never used any of the claim commands
        if 'claims' not in my_storage:
            self.protocol.send_chat_message(
                '^green;You must claim a planet first before adding players to its list.'
            )

        # assuming player is eligible to claim
        planet = self.protocol.player.planet
        on_ship = self.protocol.player.on_ship
        if not data:
            self.protocol.send_chat_message(
                '^green;You must specify a player name to add.'
            )
        else:
            addplayer = data[0]
            try:
                addplayer, rest = extract_name(data)
                addplayer = self.player_manager.get_by_name(
                    addplayer
                ).org_name
                first_name_color = self.player_manager.get_by_org_name(
                    addplayer
                ).colored_name(self.config.colors)
            except:
                self.protocol.send_chat_message(
                    '^green;There\'s no player named: ^yellow;{}'.format(
                        addplayer
                    )
                )
                return

        first_name = str(addplayer)
        orgplayer = self.protocol.player.org_name

        try:
            count = 1
            for name in self.player_planets[planet]:
                if name != str(orgplayer) and count == 1:
                    self.protocol.send_chat_message(
                        '^green;You can only claim free planets!'
                    )
                    return
                count += 1
        except:
            if first_name != orgplayer:
                self.protocol.send_chat_message(
                    '^green;Use /claim if you wish to claim a planet!'
                )
                return

        try:
            for _ in self.player_planets:
                if first_name in self.player_planets[
                    self.protocol.player.planet
                ]:
                    self.protocol.send_chat_message(
                        '^green;Player ^yellow;{}^green; is already in '
                        '^green;planet protect list.' .format(first_name_color)
                    )
                    return
        except:
            pass

        # reset planet back to current planet
        planet = self.protocol.player.planet
        if on_ship and not ('force' in ' '.join(data).lower()):
            self.protocol.send_chat_message(
                '^green;Can\'t claim ships (at the moment)'
            )
            return
        if planet == 'On Outpost':
            self.protocol.send_chat_message('^green;Instances ^red;cannot^green; be claimed.')
            self.logger.info('Claiming of an instance denied.')
            return
        if planet not in self.protected_planets:
            self.protocol.send_chat_message(
            '^green;You must claim a planet first before adding players to its list.'
        )
        else:
            if first_name:
                # make sure the command issuer is the first entry on the claims and add first_name to the list if they are.
                if first_name == orgplayer:
                        self.protocol.send_chat_message(
                            '^green;Use /claim if you wish to claim a planet!'
                        )
                        return
                elif self.player_planets[planet][0] == orgplayer:
                    self.protocol.send_chat_message('^green;Planet successfully claimed.')
                    self.logger.info('Protected planet %s', planet)
                    self.protocol.player.storage = my_storage
                    if first_name:
                        if planet not in self.player_planets:
                            self.player_planets[planet] = [first_name]
                        else:
                            self.player_planets[planet] = (
                                self.player_planets[planet] + [first_name]
                            )
                        self.protocol.send_chat_message(
                            '^green;Adding ^yellow;{}^green; to planet list.'.format(
                                first_name_color
                            )
                        )
        self.save()

    @permissions(UserLevels.GUEST)
    def claim_remove(self, data):
        """
        Removes a player from a planet's claim list. Only the owner of the planet or an admin can use this.
        Syntax: /claim_remove <player>
        """
        if self.protocol.player.planet in self.unclaimable_planets:
            self.protocol.send_chat_message(
                '^green;This planet ^red;cannot^green; be claimed!'
            )
            return
        try:
            my_storage = self.protocol.player.storage
        except AttributeError:
            return

        # set storage to 0 if player never used any of the claim commands
        if 'claims' not in my_storage:
            self.protocol.send_chat_message(
                '^green;You must claim a planet first before adding people to its list.'
            )

        # assuming player is eligible to claim
        planet = self.protocol.player.planet
        on_ship = self.protocol.player.on_ship
        if not data:
            self.protocol.send_chat_message(
                '^green;You must specify a player name to remove.'
            )
        else:
            addplayer = data[0]
            try:
                addplayer, rest = extract_name(data)
                addplayer = self.player_manager.get_by_name(
                    addplayer
                ).org_name
                first_name_color = self.player_manager.get_by_org_name(
                    addplayer
                ).colored_name(self.config.colors)
            except:
                self.protocol.send_chat_message(
                    '^green;There\'s no player named: ^yellow;{}'.format(
                        addplayer
                    )
                )
                return

        first_name = str(addplayer)
        orgplayer = self.protocol.player.org_name

        try:
            count = 1
            for name in self.player_planets[planet]:
                if name != str(orgplayer) and count == 1:
                    self.protocol.send_chat_message(
                        '^green;You can only remove players from planets you have claimed!'
                    )
                    return
                count += 1
        except:
            if first_name != orgplayer:
                self.protocol.send_chat_message(
                    '^green;Use /unclaim if you wish to unclaim a planet!'
                )
                return

        # reset planet back to current planet
        planet = self.protocol.player.planet
        if on_ship and not ('force' in ' '.join(data).lower()):
            self.protocol.send_chat_message(
                '^green;Can\'t claim ships (at the moment)'
            )
            return
        if planet not in self.protected_planets:
            self.protocol.send_chat_message(
                '^green;You have not claimed this planet.'.format(
                    first_name_color
                )
            )
        else:
            if first_name:
                #Ok, so, this is where we need to make sure the command issuer is the first entry on the claims and add first_name to the list if they are.
                if self.player_planets[planet][0] == orgplayer:
                    if first_name == orgplayer:
                        self.protocol.send_chat_message(
                            '^green;Use /unclaim if you wish to unclaim a planet!'
                        )
                        return
                    elif first_name in self.player_planets[planet]:
                        self.player_planets[planet].remove(first_name)
                        self.protocol.send_chat_message(
                            '^green;Removing ^yellow;{}^green; to planet list.'.format(
                                first_name_color
                            )
                        )
                    else:
                        self.protocol.send_chat_message(
                            '^green;Could not find ^yellow;{}^green; in planet list!'.format(
                                first_name_color
                            )
                        )
                    
            else:
                if planet not in self.player_planets:
                    self.player_planets[planet] = [first_name]
                else:
                    self.player_planets[planet] = (
                        self.player_planets[planet] + [first_name]
                    )
                self.protocol.send_chat_message(
                    '^green;Adding ^yellow;%s^green; to planet list'.format(
                        first_name_color
                    )
                )

        self.save()

    def save(self):
        self.config.config['plugin_config']['planet_protect'].update(
            {
                'protected_planets': self.protected_planets,
                'player_planets': self.player_planets
            }
        )

        self.config.plugin_config.update(
            {
                'max_claims': self.max_claims,
                'unclaimable_planets': self.unclaimable_planets
            }
        )
        self.config.save()  # save config file
