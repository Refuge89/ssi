# Copyright 2015 shiro <shiro@worldofcorecraft.com>
# This file is part of SSI.

# SSI is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# SSI is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with SSI.  If not, see <http://www.gnu.org/licenses/>.

import dbc
import os
import cparser
import struct

class Spell:
    def effect(self, e):
        pass

class Spells:
    def __init__(self, vers_str):
        hp = os.path.join(os.path.expanduser('~'), os.path.join('.ssi',
            vers_str))
        spell_path = os.path.join(hp, 'Spell.dbc')
        spell_icon_path = os.path.join(hp, 'SpellIcon.dbc')
        spell_duration_path = os.path.join(hp, 'SpellDuration.dbc')
        spell_range_path = os.path.join(hp, 'SpellRange.dbc')
        spell_radius_path = os.path.join(hp, 'SpellRadius.dbc')
        spell_casttime_path = os.path.join(hp, 'SpellCastTimes.dbc')
        shared_defs_path = os.path.join(hp, 'SharedDefines.h')

        err = RuntimeError('Could not find needed files for version.' +
            '\n\nNeed:\n' +
            spell_path + '\n' + spell_icon_path + '\n' + spell_duration_path +
            '\n' + spell_range_path + '\n' + spell_radius_path + '\n' +
            spell_casttime_path + '\n' + shared_defs_path)

        if not os.path.exists(hp) or not os.path.isdir(hp):
            raise err

        if (not os.path.exists(spell_path) or
            not os.path.exists(spell_icon_path) or
            not os.path.exists(spell_duration_path) or
            not os.path.exists(spell_range_path) or
            not os.path.exists(spell_radius_path) or
            not os.path.exists(spell_casttime_path) or
            not os.path.exists(shared_defs_path)):
            raise err

        self.spell_dbc = dbc.Dbc(spell_path, self._mapping_for_vers(vers_str),
            'id', Spell)
        self.spell_icon_dbc = dbc.Dbc(spell_icon_path, self._icon_mapping(),
            'id')
        self.spell_duration_dbc = dbc.Dbc(spell_duration_path,
            self._duration_mapping(), 'id')
        self.spell_range_dbc = dbc.Dbc(spell_range_path,
            self._range_mapping(), 'id')
        self.spell_radius_dbc = dbc.Dbc(spell_radius_path,
            self._radius_mapping(), 'id')
        self.spell_casttime_dbc = dbc.Dbc(spell_casttime_path,
            self._casttime_mapping(), 'id')

        self.parse_shared_defs(shared_defs_path)

    def cast_time(self, spell):
        """Returns cast time of spell"""
        try:
            return self.spell_casttime_dbc.table[
                spell.cast_time_index].cast_time
        except KeyError:
            return 0

    def duration(self, spell):
        """Returns duration of spell"""
        try:
            return self.spell_duration_dbc.table[spell.duration_index].duration
        except KeyError:
            return 0

    def formula(self, spell, eff):
        """Returns string representation of base points formula"""
        # XXX: spell attr calc level

        base = spell.base_points[eff] + spell.base_dice[eff] if hasattr(spell,
            'base_dice') else 0
        rng = spell.die_sides[eff]
        real_per_level = spell.real_points_per_level[eff]
        per_cp = spell.points_per_cp[eff]

        s = str(base)
        surround = False
        if rng > 1:
            s += " to " + str(base + rng)
            surround = True # If any per is added, put ( and ) around expr
        if real_per_level > 0:
            if surround:
                s = '(' + s + ') + ' + '%.2f' % real_per_level + ' * level'
                surround = False
            else:
                s += ' + %.2f' % real_per_level + ' * level'
        if per_cp > 0:
            if surround:
                s = '(' + s + ') + ' + ' %.2f' % per_cp + ' * ComboPoints'
                surround = False
            else:
                s += ' + %.2f' % per_cp + ' * ComboPoints'

        return s

    def icon_path(self, spell):
        """Returns icon path of spell"""
        return self.spell_icon_dbc.table[spell.icon_id].path
    
    def power_type(self, spell):
        """Returns string representation of power type"""
        if spell.power_type == 0xFFFFFFFE:
            return 'health'
        return [
            'mana', 'rage', 'focus', 'energy', 'happiness'][spell.power_type]

    def range(self, spell):
        """Returns range of spell"""
        return self.spell_range_dbc.table[spell.range_index]

    def _radius(self, spell, i):
        try:
            v = self.spell_radius_dbc.table[spell.radius_index[i]].radius
            return int(v) if v.is_integer() else v
        except KeyError:
            return 0
        
    def radius(self, spell):
        """Returns list of radii of spell effects"""
        return [self._radius(spell, 0), self._radius(spell, 1),
                self._radius(spell, 2)]

    def schools(self, spell):
        """Returns list of school strings"""
        l = ['physical', 'holy', 'fire', 'nature', 'frost', 'shadow', 'arcane']
        mask = self.spell_dbc.table[spell.id].school_mask
        res = []
        for i in range(0, 7):
            if mask & (1 << i):
                res.append(l[i])
        return res

    def enum_val(self, enum, id, index = -1):
        if not hasattr(self, enum) or getattr(self, enum) == None:
            return '${INVALID_ENUM}'
        e = getattr(self, enum)
        if index != -1:
            e = e[index]
            if e == None:
                return '${INVALID_ENUM}'
        for n, i in e.items():
            if id == i:
                return n
        return 'none'

    def enum_mask(self, enum, mask, bit_val = 0, index = -1):
        """bit_val: 0: use as mask value,
                    1: use i + 1
                    2: use i"""
        if not hasattr(self, enum) or getattr(self, enum) == None:
            return '${INVALID_ENUM}'
        s = ''
        for i in range(0, 64):
            if mask & (1 << i):
                if bit_val == 0:
                    v = self.enum_val(enum, 1 << i, index)
                elif bit_val == 1:
                    v = self.enum_val(enum, i + 1, index)
                else:
                    v = self.enum_val(enum, i, index)
                if v == 'none':
                    v = 'unk'
                s += ', ' + v if len(s) > 0 else v
        return s

    def iter(self, code):
        """Eval() code for each spell in DBC, returning a list of every spell
           that the code returns True for"""
        res = []
        regexp = __import__('re')
        for _, spell in self.spell_dbc.table.items():
            if eval(code,
                {'spell': spell, 're': regexp, 'spells': self}) == True:
                res.append(spell)
        return res

    def execute(self, code, result_id):
        """Exec code, handing over all spells, expecting a global variable
           of name in result_id to have a list of the ones to hand back to
           the caller"""
        scope = {'spells': self, 'dict': self.spell_dbc.table}
        exec(code, scope)
        return scope[result_id]

    def _mapping_for_vers(self, vers_str):
        if vers_str == '1.9.0':
            return _1_9_0_mappings()
        elif vers_str == '1.12.1':
            return _1_12_1_mappings()
        elif vers_str == '2.0.3':
            return _2_0_3_mappings()
        elif vers_str == '2.4.3':
            return _2_4_3_mappings()
        elif vers_str == '3.3.5':
            return _3_3_5_mappings()
        else:
            raise RuntimeError('Unsupported version "' + vers_str + '.')

    def _icon_mapping(self):
        return [dbc.Mapping(0, 'int', 'id'), dbc.Mapping(1, 'str', 'path')]

    def _duration_mapping(self):
        return [dbc.Mapping(0, 'int', 'id'),
                dbc.Mapping(1, 'int', 'duration'),
                dbc.Mapping(2, 'int', 'duration_per_level'),
                dbc.Mapping(3, 'int', 'max_duration')]

    def _range_mapping(self):
        return [dbc.Mapping(0, 'int',   'id'),
                dbc.Mapping(1, 'float', 'min'),
                dbc.Mapping(2, 'float', 'max')]

    def _radius_mapping(self):
        return [dbc.Mapping(0, 'int', 'id'), dbc.Mapping(1, 'float', 'radius')]

    def _casttime_mapping(self):
        return [dbc.Mapping(0, 'int', 'id'), dbc.Mapping(1, 'int', 'cast_time')]

    def prune_enum(self, enums, maps):
        for m in maps:
            if m[0] in enums:
                e = { k.replace(m[1], '').lower() : v for k, v in
                    enums[m[0]].items() }
                return e
        return None

    def parse_shared_defs(self, path):
        p = cparser.Parser(path, open(path))
        p.parse()
        enums = p.get_enums()
        self.attr0 = self.prune_enum(enums,
            [('SpellAttributes', 'SPELL_ATTR_'),
            ('SpellAttr0', 'SPELL_ATTR_')])
        self.attr1 = self.prune_enum(enums,
            [('SpellAttributesEx', 'SPELL_ATTR_EX_'),
            ('SpellAttr1', 'SPELL_ATTR1_')])
        self.attr2 = self.prune_enum(enums,
            [('SpellAttributesEx2', 'SPELL_ATTR_EX2_'),
            ('SpellAttr2', 'SPELL_ATTR2_')])
        self.attr3 = self.prune_enum(enums,
            [('SpellAttributesEx3', 'SPELL_ATTR_EX3_'),
            ('SpellAttr3', 'SPELL_ATTR3_')])
        self.attr4 = self.prune_enum(enums,
            [('SpellAttributesEx4', 'SPELL_ATTR_EX4_'),
            ('SpellAttr4', 'SPELL_ATTR4_')])
        self.attr5 = self.prune_enum(enums,
            [('SpellAttributesEx5', 'SPELL_ATTR_EX5_'),
            ('SpellAttr5', 'SPELL_ATTR5_')])
        self.attr6 = self.prune_enum(enums,
            [('SpellAttributesEx6', 'SPELL_ATTR_EX6_'),
            ('SpellAttr6', 'SPELL_ATTR6_')])
        self.attr7 = self.prune_enum(enums,
            [('SpellAttributesEx7', 'SPELL_ATTR_EX7_'),
            ('SpellAttr7', 'SPELL_ATTR7_')])
        self.effects = self.prune_enum(enums,
            [('SpellEffects', 'SPELL_EFFECT_'),
            ('SpellEffectName', 'SPELL_EFFECT_')])
        self.auras = self.prune_enum(enums, [('AuraType', 'SPELL_AURA_')])
        self.mechanics = self.prune_enum(enums, [('Mechanics', 'MECHANIC_')])
        self.spell_class = self.prune_enum(enums,
            [('SpellDmgClass', 'SPELL_DAMAGE_CLASS_')])
        self.preventions = self.prune_enum(enums,
            [('SpellPreventionType', 'SPELL_PREVENTION_TYPE_')])
        self.dispels = self.prune_enum(enums,
            [('DispelType', 'DISPEL_')])
        self.targets = self.prune_enum(enums, [('Targets', 'TARGET_')])
        self.proc_flags = self.prune_enum(enums, [('ProcFlags', 'PROC_FLAG_')])
        self.families = self.prune_enum(enums,
            [('SpellFamilyNames', 'SPELLFAMILY_'),
            ('SpellFamily', 'SPELLFAMILY_')])
        self.interrupts = self.prune_enum(enums,
            [('SpellInterruptFlags', 'SPELL_INTERRUPT_FLAG_')])
        self.channel_interrupts = self.prune_enum(enums,
            [('SpellChannelInterruptFlags', 'CHANNEL_FLAG_')])
        self.aura_interrupts = self.prune_enum(enums,
            [('SpellAuraInterruptFlags', 'AURA_INTERRUPT_FLAG_')])
        self.target_flags = self.prune_enum(enums,
            [('SpellCastTargetFlags', 'TARGET_FLAG_')])
        self.stances = self.prune_enum(enums, [('ShapeshiftForm', 'FORM_')])
        self.inv_slots = self.prune_enum(enums,
            [('InventoryType', 'INVTYPE_')])
        self.item_class = self.prune_enum(enums, [('ItemClass', 'ITEM_CLASS_')])

        # item sub-classes
        self.sub_class = {
            0: self.prune_enum(enums,
                [('ItemSubclassConsumable', 'ITEM_SUBCLASS_')]),
            1: self.prune_enum(enums,
                [('ItemSubclassContainer', 'ITEM_SUBCLASS_')]),
            2: self.prune_enum(enums,
                [('ItemSubclassWeapon', 'ITEM_SUBCLASS_WEAPON_')]),
            3: self.prune_enum(enums,
                [('ItemSubclassGem', 'ITEM_SUBCLASS_GEM_')]),
            4: self.prune_enum(enums,
                [('ItemSubclassArmor', 'ITEM_SUBCLASS_ARMOR_')]),
            5: self.prune_enum(enums,
                [('ItemSubclassReagent', 'ITEM_SUBCLASS_')]),
            6: self.prune_enum(enums,
                [('ItemSubclassProjectile', 'ITEM_SUBCLASS_')]),
            7: self.prune_enum(enums,
                [('ItemSubclassTradeGoods', 'ITEM_SUBCLASS_')]),
            8: self.prune_enum(enums,
                [('ItemSubclassGeneric', 'ITEM_SUBCLASS_')]),
            9: self.prune_enum(enums,
                [('ItemSubclassRecipe', 'ITEM_SUBCLASS_')]),
            10: self.prune_enum(enums,
                [('ItemSubclassMoney', 'ITEM_SUBCLASS_')]),
            11: self.prune_enum(enums,
                [('ItemSubclassQuiver', 'ITEM_SUBCLASS_')]),
            12: self.prune_enum(enums,
                [('ItemSubclassQuest', 'ITEM_SUBCLASS_')]),
            13: self.prune_enum(enums,
                [('ItemSubclassKey', 'ITEM_SUBCLASS_')]),
            14: self.prune_enum(enums,
                [('ItemSubclassPermanent', 'ITEM_SUBCLASS_')]),
            15: self.prune_enum(enums,
                [('ItemSubclassJunk', 'ITEM_SUBCLASS_JUNK_')]),
            16: self.prune_enum(enums,
                [('ItemSubclassGlyph', 'ITEM_SUBCLASS_GLYPH_')]),
            }

def _1_9_0_mappings():
    return [
        dbc.Mapping(0,   'int',   'id'),
        dbc.Mapping(1,   'int',   'school_mask',
            post_process = lambda x, _: (1 << x)),
        dbc.Mapping(2,   'int',   'category'),
        dbc.Mapping(4,   'int',   'dispel'),
        dbc.Mapping(5,   'int',   'mechanic'),
        dbc.Mapping(6,   'int',   'attr', count = 3),
        dbc.Mapping(9,  'int',   'stances'),
        dbc.Mapping(10,  'int',   'stances_not'),
        dbc.Mapping(11,  'int',   'target_mask'),
        dbc.Mapping(16,  'int',   'cast_time_index'),
        dbc.Mapping(17,  'int',   'cooldown'),
        dbc.Mapping(18,  'int',   'category_cooldown'),
        dbc.Mapping(19,  'int',   'interrupt_flags'),
        dbc.Mapping(20,  'int',   'aura_interrupt_flags'),
        dbc.Mapping(21,  'int',   'channel_interrupt_flags'),
        dbc.Mapping(22,  'int',   'proc_flags'),
        dbc.Mapping(23,  'int',   'proc_chance'),
        dbc.Mapping(24,  'int',   'proc_charges'),
        dbc.Mapping(25,  'int',   'max_level'),
        dbc.Mapping(26,  'int',   'base_level'),
        dbc.Mapping(27,  'int',   'level'),
        dbc.Mapping(28,  'int',   'duration_index'),
        dbc.Mapping(29,  'int',   'power_type'),
        dbc.Mapping(30,  'int',   'power'),
        dbc.Mapping(34,  'int',   'range_index'),
        dbc.Mapping(35,  'float', 'speed'),
        dbc.Mapping(37,  'int',   'stacks'),
        dbc.Mapping(56,  'sint',  'item_class'),
        dbc.Mapping(57,  'int',   'item_subclass', post_process =
            lambda x, _: 0 if x == 0xFFFFFFFF else x),
        dbc.Mapping(57,  'int',   'inv_slot', post_process =
            lambda x, _: 0), # TODO: Is this not present?
        dbc.Mapping(58,  'int',   'effect', count = 3),
        dbc.Mapping(61,  'int',   'die_sides', count = 3),
        dbc.Mapping(64,  'int',   'base_dice', count = 3),
        dbc.Mapping(70,  'float', 'real_points_per_level', count = 3),
        dbc.Mapping(73,  'sint',  'base_points', count = 3),
        dbc.Mapping(76,  'sint',  'mechanic_effect', count = 3),
        dbc.Mapping(79,  'int',   'target_a', count = 3),
        dbc.Mapping(82,  'int',   'target_b', count = 3),
        dbc.Mapping(85,  'int',   'radius_index', count = 3),
        dbc.Mapping(88,  'int',   'aura', count = 3),
        dbc.Mapping(91,  'int',   'amplitude', count = 3),
        dbc.Mapping(94, 'float',  'multiple_value', count = 3),
        dbc.Mapping(97, 'int',   'chain', count = 3),
        dbc.Mapping(103, 'int',   'misc_a', count = 3),
        dbc.Mapping(106, 'int',   'trigger', count = 3),
        dbc.Mapping(109, 'float', 'points_per_cp', count = 3),
        dbc.Mapping(114, 'int',   'icon_id'),
        dbc.Mapping(117, 'str',   'name'),
        dbc.Mapping(126, 'str',   'rank'),
        dbc.Mapping(144, 'str',   'tooltip'),
        dbc.Mapping(154, 'int',   'gcd_category'),
        dbc.Mapping(155, 'int',   'gcd'),
        dbc.Mapping(156, 'int',   'max_target_level'),
        dbc.Mapping(157, 'int',   'spell_family'),
        dbc.Mapping(158, 'long',  'spell_mask'),
        dbc.Mapping(159, 'int',   'max_targets'),
        dbc.Mapping(160, 'int',   'spell_class'),
        dbc.Mapping(161, 'int',   'prevention'),
        dbc.Mapping(163, 'float', 'dmg_multiplier', count = 3),
    ]

def _1_12_1_mappings():
    return [
        dbc.Mapping(0,   'int',   'id'),
        dbc.Mapping(1,   'int',   'school_mask',
            post_process = lambda x, _: (1 << x)),
        dbc.Mapping(2,   'int',   'category'),
        dbc.Mapping(4,   'int',   'dispel'),
        dbc.Mapping(5,   'int',   'mechanic'),
        dbc.Mapping(6,   'int',   'attr', count = 5),
        dbc.Mapping(11,  'int',   'stances'),
        dbc.Mapping(12,  'int',   'stances_not'),
        dbc.Mapping(13,  'int',   'target_mask'),
        dbc.Mapping(18,  'int',   'cast_time_index'),
        dbc.Mapping(19,  'int',   'cooldown'),
        dbc.Mapping(20,  'int',   'category_cooldown'),
        dbc.Mapping(21,  'int',   'interrupt_flags'),
        dbc.Mapping(22,  'int',   'aura_interrupt_flags'),
        dbc.Mapping(23,  'int',   'channel_interrupt_flags'),
        dbc.Mapping(24,  'int',   'proc_flags'),
        dbc.Mapping(25,  'int',   'proc_chance'),
        dbc.Mapping(26,  'int',   'proc_charges'),
        dbc.Mapping(27,  'int',   'max_level'),
        dbc.Mapping(28,  'int',   'base_level'),
        dbc.Mapping(29,  'int',   'level'),
        dbc.Mapping(30,  'int',   'duration_index'),
        dbc.Mapping(31,  'int',   'power_type'),
        dbc.Mapping(32,  'int',   'power'),
        dbc.Mapping(36,  'int',   'range_index'),
        dbc.Mapping(37,  'float', 'speed'),
        dbc.Mapping(39,  'int',   'stacks'),
        dbc.Mapping(58,  'sint',  'item_class'),
        dbc.Mapping(59,  'int',   'item_subclass', post_process =
            lambda x, _: 0 if x == 0xFFFFFFFF else x),
        dbc.Mapping(60,  'int',   'inv_slot'),
        dbc.Mapping(61,  'int',   'effect', count = 3),
        dbc.Mapping(64,  'int',   'die_sides', count = 3),
        dbc.Mapping(67,  'int',   'base_dice', count = 3),
        dbc.Mapping(73,  'float', 'real_points_per_level', count = 3),
        dbc.Mapping(76,  'sint',  'base_points', count = 3),
        dbc.Mapping(79,  'sint',  'mechanic_effect', count = 3),
        dbc.Mapping(82,  'int',   'target_a', count = 3),
        dbc.Mapping(85,  'int',   'target_b', count = 3),
        dbc.Mapping(88,  'int',   'radius_index', count = 3),
        dbc.Mapping(91,  'int',   'aura', count = 3),
        dbc.Mapping(94,  'int',   'amplitude', count = 3),
        dbc.Mapping(97, 'float',  'multiple_value', count = 3),
        dbc.Mapping(100, 'int',   'chain', count = 3),
        dbc.Mapping(106, 'int',   'misc_a', count = 3),
        dbc.Mapping(109, 'int',   'trigger', count = 3),
        dbc.Mapping(112, 'float', 'points_per_cp', count = 3),
        dbc.Mapping(117, 'int',   'icon_id'),
        dbc.Mapping(120, 'str',   'name'),
        dbc.Mapping(129, 'str',   'rank'),
        dbc.Mapping(147, 'str',   'tooltip'),
        dbc.Mapping(157, 'int',   'gcd_category'),
        dbc.Mapping(158, 'int',   'gcd'),
        dbc.Mapping(159, 'int',   'max_target_level'),
        dbc.Mapping(160, 'int',   'spell_family'),
        dbc.Mapping(161, 'long',  'spell_mask'),
        dbc.Mapping(163, 'int',   'max_targets'),
        dbc.Mapping(164, 'int',   'spell_class'),
        dbc.Mapping(165, 'int',   'prevention'),
        dbc.Mapping(167, 'float', 'dmg_multiplier', count = 3),
    ]

def _2_0_3_mappings():
    return [
        dbc.Mapping(0,   'int',   'id'),
        dbc.Mapping(1,   'int',   'school_mask',
            post_process = lambda x, _: (1 << x)),
        dbc.Mapping(2,   'int',   'category'),
        dbc.Mapping(4,   'int',   'dispel'),
        dbc.Mapping(5,   'int',   'mechanic'),
        dbc.Mapping(6,   'int',   'attr', count = 6),
        dbc.Mapping(12,  'int',   'stances'),
        dbc.Mapping(13,  'int',   'stances_not'),
        dbc.Mapping(14,  'int',   'target_mask'),
        dbc.Mapping(21,  'int',   'cast_time_index'),
        dbc.Mapping(22,  'int',   'cooldown'),
        dbc.Mapping(23,  'int',   'category_cooldown'),
        dbc.Mapping(24,  'int',   'interrupt_flags'),
        dbc.Mapping(25,  'int',   'aura_interrupt_flags'),
        dbc.Mapping(26,  'int',   'channel_interrupt_flags'),
        dbc.Mapping(27,  'int',   'proc_flags'),
        dbc.Mapping(28,  'int',   'proc_chance'),
        dbc.Mapping(29,  'int',   'proc_charges'),
        dbc.Mapping(30,  'int',   'max_level'),
        dbc.Mapping(31,  'int',   'base_level'),
        dbc.Mapping(32,  'int',   'level'),
        dbc.Mapping(33,  'int',   'duration_index'),
        dbc.Mapping(34,  'int',   'power_type'),
        dbc.Mapping(35,  'int',   'power'),
        dbc.Mapping(39,  'int',   'range_index'),
        dbc.Mapping(40,  'float', 'speed'),
        dbc.Mapping(42,  'int',   'stacks'),
        dbc.Mapping(61,  'sint',  'item_class'),
        dbc.Mapping(62,  'int',   'item_subclass', post_process =
            lambda x, _: 0 if x == 0xFFFFFFFF else x),
        dbc.Mapping(63,  'int',   'inv_slot'),
        dbc.Mapping(64,  'int',   'effect', count = 3),
        dbc.Mapping(67,  'int',   'die_sides', count = 3),
        dbc.Mapping(70,  'int',   'base_dice', count = 3),
        dbc.Mapping(76,  'float', 'real_points_per_level', count = 3),
        dbc.Mapping(79,  'sint',  'base_points', count = 3),
        dbc.Mapping(82,  'sint',  'mechanic_effect', count = 3),
        dbc.Mapping(85,  'int',   'target_a', count = 3),
        dbc.Mapping(88,  'int',   'target_b', count = 3),
        dbc.Mapping(91,  'int',   'radius_index', count = 3),
        dbc.Mapping(94,  'int',   'aura', count = 3),
        dbc.Mapping(97,  'int',   'amplitude', count = 3),
        dbc.Mapping(100, 'float', 'multiple_value', count = 3),
        dbc.Mapping(103, 'int',   'chain', count = 3),
        dbc.Mapping(109, 'int',   'misc_a', count = 3),
        dbc.Mapping(112, 'int',   'misc_b', count = 3),
        dbc.Mapping(115, 'int',   'trigger', count = 3),
        dbc.Mapping(117, 'float', 'points_per_cp', count = 3),
        dbc.Mapping(120, 'int',   'icon_id'),
        dbc.Mapping(123, 'str',   'name'),
        dbc.Mapping(132, 'str',   'rank'),
        dbc.Mapping(150, 'str',   'tooltip'),
        dbc.Mapping(160, 'int',   'gcd_category'),
        dbc.Mapping(161, 'int',   'gcd'),
        dbc.Mapping(162, 'int',   'max_target_level'),
        dbc.Mapping(163, 'int',   'spell_family'),
        dbc.Mapping(164, 'long',  'spell_mask'),
        dbc.Mapping(166, 'int',   'max_targets'),
        dbc.Mapping(167, 'int',   'spell_class'),
        dbc.Mapping(168, 'int',   'prevention'),
        dbc.Mapping(170, 'float', 'dmg_multiplier', count = 3),
    ]

def _2_4_3_mappings():
    return [
        dbc.Mapping(0,   'int',   'id'),
        dbc.Mapping(1,   'int',   'category'),
        dbc.Mapping(3,   'int',   'dispel'),
        dbc.Mapping(4,   'int',   'mechanic'),
        dbc.Mapping(5,   'int',   'attr', count = 7),
        dbc.Mapping(12,  'int',   'stances'),
        dbc.Mapping(13,  'int',   'stances_not'),
        dbc.Mapping(14,  'int',   'target_mask'),
        dbc.Mapping(22,  'int',   'cast_time_index'),
        dbc.Mapping(23,  'int',   'cooldown'),
        dbc.Mapping(24,  'int',   'category_cooldown'),
        dbc.Mapping(25,  'int',   'interrupt_flags'),
        dbc.Mapping(26,  'int',   'aura_interrupt_flags'),
        dbc.Mapping(27,  'int',   'channel_interrupt_flags'),
        dbc.Mapping(28,  'int',   'proc_flags'),
        dbc.Mapping(29,  'int',   'proc_chance'),
        dbc.Mapping(30,  'int',   'proc_charges'),
        dbc.Mapping(31,  'int',   'max_level'),
        dbc.Mapping(32,  'int',   'base_level'),
        dbc.Mapping(33,  'int',   'level'),
        dbc.Mapping(34,  'int',   'duration_index'),
        dbc.Mapping(35,  'int',   'power_type'),
        dbc.Mapping(36,  'int',   'power'),
        dbc.Mapping(40,  'int',   'range_index'),
        dbc.Mapping(41,  'float', 'speed'),
        dbc.Mapping(43,  'int',   'stacks'),
        dbc.Mapping(62,  'sint',  'item_class'),
        dbc.Mapping(63,  'int',   'item_subclass'),
        dbc.Mapping(64,  'int',   'inv_slot'),
        dbc.Mapping(65,  'int',   'effect', count = 3),
        dbc.Mapping(68,  'int',   'die_sides', count = 3),
        dbc.Mapping(71,  'int',   'base_dice', count = 3),
        dbc.Mapping(77,  'float', 'real_points_per_level', count = 3),
        dbc.Mapping(80,  'sint',  'base_points', count = 3),
        dbc.Mapping(83,  'sint',  'mechanic_effect', count = 3),
        dbc.Mapping(86,  'int',   'target_a', count = 3),
        dbc.Mapping(89,  'int',   'target_b', count = 3),
        dbc.Mapping(92,  'int',   'radius_index', count = 3),
        dbc.Mapping(95,  'int',   'aura', count = 3),
        dbc.Mapping(98,  'int',   'amplitude', count = 3),
        dbc.Mapping(101, 'float', 'multiple_value', count = 3),
        dbc.Mapping(104, 'int',   'chain', count = 3),
        dbc.Mapping(110, 'int',   'misc_a', count = 3),
        dbc.Mapping(113, 'int',   'misc_b', count = 3),
        dbc.Mapping(116, 'int',   'trigger', count = 3),
        dbc.Mapping(119, 'float', 'points_per_cp', count = 3),
        dbc.Mapping(124, 'int',   'icon_id'),
        dbc.Mapping(127, 'str',   'name'),
        dbc.Mapping(144, 'str',   'rank'),
        dbc.Mapping(178, 'str',   'tooltip'),
        dbc.Mapping(196, 'int',   'gcd_category'),
        dbc.Mapping(197, 'int',   'gcd'),
        dbc.Mapping(198, 'int',   'max_target_level'),
        dbc.Mapping(199, 'int',   'spell_family'),
        dbc.Mapping(200, 'long',  'spell_mask'),
        dbc.Mapping(202, 'int',   'max_targets'),
        dbc.Mapping(203, 'int',   'spell_class'),
        dbc.Mapping(204, 'int',   'prevention'),
        dbc.Mapping(206, 'float', 'dmg_multiplier', count = 3),
        dbc.Mapping(215, 'int',   'school_mask'),
    ]

def flag12bytes(val, spell):
    return (val << 64) | (spell._spell_mask1 << 32) | spell._spell_mask0 

def _3_3_5_mappings():
    return [
        dbc.Mapping(0,   'int',   'id'),
        dbc.Mapping(1,   'int',   'category'),
        dbc.Mapping(2,   'int',   'dispel'),
        dbc.Mapping(3,   'int',   'mechanic'),
        dbc.Mapping(4,   'int',   'attr', count = 8),
        dbc.Mapping(12,  'int',   'stances'),
        dbc.Mapping(14,  'int',   'stances_not'),
        dbc.Mapping(16,  'int',   'target_mask'),
        dbc.Mapping(28,  'int',   'cast_time_index'),
        dbc.Mapping(29,  'int',   'cooldown'),
        dbc.Mapping(30,  'int',   'category_cooldown'),
        dbc.Mapping(31,  'int',   'interrupt_flags'),
        dbc.Mapping(32,  'int',   'aura_interrupt_flags'),
        dbc.Mapping(33,  'int',   'channel_interrupt_flags'),
        dbc.Mapping(34,  'int',   'proc_flags'),
        dbc.Mapping(35,  'int',   'proc_chance'),
        dbc.Mapping(36,  'int',   'proc_charges'),
        dbc.Mapping(37,  'int',   'max_level'),
        dbc.Mapping(38,  'int',   'base_level'),
        dbc.Mapping(39,  'int',   'level'),
        dbc.Mapping(40,  'int',   'duration_index'),
        dbc.Mapping(41,  'int',   'power_type'),
        dbc.Mapping(42,  'int',   'power'),
        dbc.Mapping(46,  'int',   'range_index'),
        dbc.Mapping(47,  'float', 'speed'),
        dbc.Mapping(49,  'int',   'stacks'),
        dbc.Mapping(68,  'sint',  'item_class'),
        dbc.Mapping(69,  'int',   'item_subclass'),
        dbc.Mapping(70,  'int',   'inv_slot'),
        dbc.Mapping(71,  'int',   'effect', count = 3),
        dbc.Mapping(74,  'int',   'die_sides', count = 3),
        #dbc.Mapping(71,  'int',   'base_dice', count = 3),
        dbc.Mapping(77,  'float', 'real_points_per_level', count = 3),
        dbc.Mapping(80,  'sint',  'base_points', count = 3),
        dbc.Mapping(83,  'sint',  'mechanic_effect', count = 3),
        dbc.Mapping(86,  'int',   'target_a', count = 3),
        dbc.Mapping(89,  'int',   'target_b', count = 3),
        dbc.Mapping(92,  'int',   'radius_index', count = 3),
        dbc.Mapping(95,  'int',   'aura', count = 3),
        dbc.Mapping(98,  'int',   'amplitude', count = 3),
        dbc.Mapping(101, 'float', 'multiple_value', count = 3),
        dbc.Mapping(104, 'int',   'chain', count = 3),
        dbc.Mapping(110, 'int',   'misc_a', count = 3),
        dbc.Mapping(113, 'int',   'misc_b', count = 3),
        dbc.Mapping(116, 'int',   'trigger', count = 3),
        dbc.Mapping(119, 'float', 'points_per_cp', count = 3),
        dbc.Mapping(133, 'int',   'icon_id'),
        dbc.Mapping(136, 'str',   'name'),
        dbc.Mapping(153, 'str',   'rank'),
        dbc.Mapping(187, 'str',   'tooltip'),
        dbc.Mapping(205, 'int',   'gcd_category'),
        dbc.Mapping(206, 'int',   'gcd'),
        dbc.Mapping(207, 'int',   'max_target_level'),
        dbc.Mapping(208, 'int',   'spell_family'),
        dbc.Mapping(200, 'int',   '_spell_mask0'),
        dbc.Mapping(201, 'int',   '_spell_mask1'),
        dbc.Mapping(202, 'int',   'spell_mask', post_process = flag12bytes),
        dbc.Mapping(212, 'int',   'max_targets'),
        dbc.Mapping(213, 'int',   'spell_class'),
        dbc.Mapping(214, 'int',   'prevention'),
        dbc.Mapping(216, 'float', 'dmg_multiplier', count = 3),
        dbc.Mapping(225, 'int',   'school_mask'),
    ]
