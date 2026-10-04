"""Regression tests using Home Assistant's real EventEntity implementation."""
import asyncio
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from custom_components.xiaomi_home.event import Event  # pylint: disable=wrong-import-position


class LockEventMappingTest(unittest.IsolatedAsyncioTestCase):
    """Exercise subscription, raw argument parsing, and HA event validation."""

    def make_entity(
        self, model='loock.lock.t1', siid=5, eiid=1,
        service_name='door', argument_name='异常情况', with_condition=True,
    ):
        """Create an isolated entity without connecting to a real device."""
        service = SimpleNamespace(
            iid=siid, name=service_name, description_trans='门')
        argument = SimpleNamespace(
            iid=2, name='abnormal-condition',
            description_trans=argument_name)
        timestamp = SimpleNamespace(
            iid=3, name='current-time', description_trans='当前时间')
        spec = SimpleNamespace(
            service=service, iid=eiid, name='exception-occurred',
            description_trans='发生异常', proprietary=False,
            platform='event', device_class=None,
            argument=([argument, timestamp] if with_condition else [timestamp]))
        device = SimpleNamespace(
            model=model, name='Test lock', online=True,
            miot_client=SimpleNamespace(main_loop=asyncio.get_running_loop()),
            gen_event_entity_id=lambda **kwargs:
            f"{kwargs['ha_domain']}.test_exception_occurred_e_{siid}_{eiid}",
            sub_device_state=lambda **kwargs: 1,
        )
        device.sub_event = lambda **kwargs: setattr(
            device, 'event_handler', kwargs['handler']) or 1
        entity = Event(miot_device=device, spec=spec)
        return entity, device

    async def deliver(self, entity, device, arguments):
        """Deliver an upstream packet through the registered callback."""
        await entity.async_added_to_hass()
        with patch.object(entity, 'async_write_ha_state') as write_state:
            device.event_handler({'arguments': arguments}, None)
        write_state.assert_called_once()

    async def test_known_conditions_and_original_attributes(self):
        for code, expected in (
            (1, '关门'), (2, '开门超时'), (4, '门被破坏'), (5, '门卡住')
        ):
            with self.subTest(code=code):
                entity, device = self.make_entity()
                await self.deliver(entity, device, [
                    {'piid': 2, 'value': code},
                    {'piid': 3, 'value': 1700000000},
                ])
                self.assertEqual(
                    entity.state_attributes['event_type'], expected)
                self.assertIn(expected, entity.event_types)
                self.assertEqual(entity.state_attributes['异常情况'], code)
                self.assertEqual(entity.state_attributes['当前时间'], 1700000000)
                self.assertEqual(entity.entity_id,
                                 'event.test_exception_occurred_e_5_1')
                self.assertEqual(entity.unique_id,
                                 'xiaomi_home.test_exception_occurred_e_5_1')

    async def test_cloud_packed_arguments_and_translated_argument(self):
        entity, device = self.make_entity(argument_name='Abnormal Condition')
        await self.deliver(entity, device, [{'value': [2, 1700000000]}])
        self.assertEqual(entity.state_attributes['event_type'], '开门超时')
        self.assertEqual(entity.state_attributes['Abnormal Condition'], 2)

    async def test_unknown_missing_and_malformed_conditions(self):
        for value in (99, None, True, 1.0, [], {}, 'unexpected'):
            with self.subTest(value=value):
                entity, device = self.make_entity()
                await self.deliver(
                    entity, device, [{'piid': 2, 'value': value}])
                self.assertEqual(
                    entity.state_attributes['event_type'], '发生异常')
        entity, device = self.make_entity()
        await self.deliver(entity, device, [])
        self.assertEqual(entity.state_attributes['event_type'], '发生异常')

    async def test_numeric_string_condition(self):
        entity, device = self.make_entity()
        await self.deliver(entity, device, [{'piid': 2, 'value': '1'}])
        self.assertEqual(entity.state_attributes['event_type'], '关门')

    async def test_other_models_services_and_events_unchanged(self):
        for options in (
            {'model': 'other.lock'}, {'siid': 2}, {'eiid': 4},
            {'service_name': 'lock'}, {'with_condition': False},
        ):
            with self.subTest(options=options):
                entity, device = self.make_entity(**options)
                arguments = [] if options.get('with_condition') is False else [
                    {'piid': 2, 'value': 1}]
                await self.deliver(entity, device, arguments)
                self.assertEqual(entity.event_types, ['发生异常'])
                self.assertEqual(entity.state_attributes['event_type'], '发生异常')

    async def test_repeated_close_events_keep_distinct_timestamps(self):
        entity, device = self.make_entity()
        await self.deliver(entity, device, [{'piid': 2, 'value': 1}])
        first = entity.state
        with patch.object(entity, 'async_write_ha_state'):
            device.event_handler({'arguments': [{'piid': 2, 'value': 1}]}, None)
        self.assertGreater(entity.state, first)
        self.assertEqual(entity.state_attributes['event_type'], '关门')


if __name__ == '__main__':
    unittest.main()
